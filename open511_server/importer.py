from copy import deepcopy
import datetime
import logging
try:
    from urlparse import urljoin, parse_qsl
    from urllib import urlencode
except ImportError:
    from urllib.parse import urljoin, parse_qsl, urlencode

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

        self.post_import(created)

        if self.persist_status:
            self.status['objects_imported'] = len(created)
            self.status['counter'] = self.status.get('counter', 0) + 1
            self.last_run_obj.status_info = self.status
            self.last_run_obj.save()

        logger.info('Importer {} ran, created {} objects'.format(self.id, len(created)))

    def fetch(self):
        raise NotImplementedError

    def convert(self, input_document):
        raise NotImplementedError

    def post_import(self, imported):
        pass

    def archive_existing(self, imported):
        if not len(imported):
            return
        if len(set(o.jurisdiction_id for o in imported)) != 1:
            return logger.error("Not archiving because events are from different jurisdictions")
        jur = imported[0].jurisdiction
        updated = self.model.objects.filter(jurisdiction=jur, active=True).exclude(
            id__in=[o.id for o in imported]).update(active=False)
        if updated:
            logger.info("{} events archived".format(updated))
        return updated

    def save(self, xml_obj):
        save_opts = {}
        if self.default_language:
            save_opts['default_language'] = self.default_language
        if self.base_url:
            save_opts['base_url'] = self.base_url
        obj_created, obj = self.model.objects.update_or_create_from_xml(xml_obj, **save_opts)
        yield obj

    def _logging_iterable(self, iterable, step_name, exceptions=(Exception,)):
        iterator = iter(iterable)
        while True:
            try:
                yield next(iterator)
            except StopIteration:
                raise
            except exceptions as e:
                logger.exception("{} importing, during {} step: {}".format(
                    e.__class__.__name__, step_name, e))

class Open511Importer(BaseImporter):

    def _fetch_url(self, url):
        resp = requests.get(url, headers={
            'Accept': 'application/xml',
            'Open511-Version': settings.OPEN511_DEFAULT_VERSION
        })
        return etree.fromstring(resp.content)

    def fetch(self):
        next_url, _, query = self.opts['URL'].partition('?')
        query = dict(parse_qsl(query)) if query else {}

        self.active_update = bool(
            self.opts.get('ACTIVE_UPDATES_ONLY') or
            (self.opts.get('ACTIVE_UPDATES_EVERY') != 0 and
                self.status.get('counter', 0) % self.opts.get('ACTIVE_UPDATES_EVERY', 500) == 0)
        )

        if not self.active_update:
            query['status'] = 'ALL'
            if self.status.get('max_updated'):
                query['updated'] = '>=' + self.status['max_updated']

        next_url = next_url + '?' + urlencode(query)

        while next_url is not None:
            root = self._fetch_url(next_url)
            assert root.tag == 'open511'

            if root.get(XML_LANG):
                self.default_language = root.get(XML_LANG)

            if root.get(XML_BASE):
                self.base_url = root.get(XML_BASE)
            else:
                self.base_url = next_url

            if not self.active_update:
                self.status['max_updated'] = max(
                    root.xpath('events/event/updated/text()') + [self.status.get('max_updated', '')])

            for xml_obj in root.xpath('events/event'):
                yield xml_obj

            next_link = root.xpath('pagination/link[@rel="next"]')
            if next_link:
                next_url = urljoin(next_url, next_link[0].get('href'))
            else:
                next_url = None

    def convert(self, input_document):
        yield input_document

    def post_import(self, imported):
        if getattr(self, 'active_update', False):
            updated = self.archive_existing(imported)
            self.status['last_active_update'] = '{} {}'.format(datetime.datetime.now().isoformat(), updated)

