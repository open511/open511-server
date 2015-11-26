from copy import deepcopy
import logging
try:
    from urlparse import urljoin
except ImportError:
    from urllib.parse import urljoin

from django.conf import settings
from django.core.exceptions import ValidationError

from lxml import etree
import requests

from open511.utils.serialization import XML_LANG, XML_BASE
from open511.validator import Open511ValidationError
from open511_server.models import RoadEvent, ImportTaskStatus


logger = logging.getLogger(__name__)

class BaseImporter(object):

    default_language = None
    base_url = None

    def __init__(self, opts, persist_status=False):
        self.opts = opts
        self.model = RoadEvent
        self.persist_status = persist_status
        self.last_run_status = {}
        self.status = {}

    @property
    def id(self):
        if 'ID' in self.opts:
            return self.opts['ID']
        return self.opts['URL']

    def run(self):

        if self.persist_status:
            try:
                self.last_run_obj = ImportTaskStatus.objects.get(id=self.id)
            except ImportTaskStatus.DoesNotExist:
                self.last_run_obj = ImportTaskStatus.objects.create(id=self.id)
            self.last_run_status = self.last_run_obj.status_info
            self.status = deepcopy(self.last_run_status)

        created = []

        for input_document in self._logging_iterable(self.fetch(), 'fetch'):

            for o5_xml_obj in self._logging_iterable(self.convert(input_document), 'conversion'):

                for db_obj in self._logging_iterable(self.save(o5_xml_obj), 'save',
                        exceptions=(ValueError, ValidationError, Open511ValidationError)):

                    logger.debug("Imported %s %s" % (o5_xml_obj.tag, db_obj.id))
                    created.append(db_obj)

        if self.persist_status:
            self.status['objects_imported'] = len(created)
            self.last_run_obj.status_info = self.status
            self.last_run_obj.save()

        print('Importer {} ran, created {} objects'.format(self.id, len(created)))

    def fetch(self):
        raise NotImplementedError

    def convert(self, input_document):
        raise NotImplementedError

    def save(self, xml_obj):
        save_opts = {}
        if self.default_language:
            save_opts['default_language'] = self.default_language
        if self.base_url:
            save_opts['base_url'] = self.base_url
        yield self.model.objects.update_or_create_from_xml(xml_obj, **save_opts)

    def _logging_iterable(self, iterable, step_name, exceptions=(Exception,)):
        iterator = iter(iterable)
        while True:
            try:
                yield next(iterator)
            except StopIteration:
                raise
            except exceptions as e:
                logger.error("{} importing, during {} step: {}".format(
                    e.__class__.__name__, step_name, e))

class Open511Importer(BaseImporter):

    def _fetch_url(self, url):
        resp = requests.get(url, headers={
            'Accept': 'application/xml',
            'Open511-Version': settings.OPEN511_DEFAULT_VERSION
        })
        return etree.fromstring(resp.content)

    def fetch(self):
        next_url = self.opts['URL']
        # FIXME add updated param
        while next_url is not None:
            root = self._fetch_url(next_url)
            assert root.tag == 'open511'

            if root.get(XML_LANG):
                self.default_language = root.get(XML_LANG)

            if root.get(XML_BASE):
                self.base_url = root.get(XML_BASE)
            else:
                self.base_url = next_url

            for xml_obj in root.xpath('events/event'):
                yield xml_obj

            next_link = root.xpath('pagination/link[@rel="next"]')
            if next_link:
                next_url = urljoin(next_url, next_link[0].get('href'))
            else:
                next_url = None

    def convert(self, input_document):
        yield input_document


