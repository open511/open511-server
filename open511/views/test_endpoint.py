from django.http import HttpResponse
from django.views.generic import View

from lxml import etree

from open511.models import Jurisdiction, RoadEvent
from open511.utils.serialization import XML_LANG


class TestEndpointView(View):

    def post(self, request):
        if request.POST['command'] == 'clear':
            self._clear()
        elif request.POST['command'] == 'load':
            self._load_xml(request.POST['xml'])

        return HttpResponse('OK')

    def _clear(self):
        try:
            jur = Jurisdiction.objects.get(slug='test.open511.org')
        except Jurisdiction.DoesNotExist:
            jur = Jurisdiction(slug='test.open511.org')
        jur.xml_data = """<jurisdiction xmlns:atom="http://www.w3.org/2005/Atom" xmlns:gml="http://www.opengis.net/gml">
            <name xml:lang="en">TEST</name>
            <timezone>America/Montreal</timezone>
            <email>contact@open511.org</email>
            <atom:link rel="geography" href="http://test.open511.org/"/>
            <atom:link rel="license" href="http://test.open511.org/"/>
            </jurisdiction>"""
        jur.save()

        RoadEvent.objects.filter(jurisdiction=jur).delete()

    def _load_xml(self, xml):
        root = etree.fromstring(xml)
        assert root.tag == 'open511'
        opts = {
            'default_jurisdiction': Jurisdiction.objects.get(slug='test.open511.org')
        }
        if root.get(XML_LANG):
            opts['default_language'] = root.get(XML_LANG)
        for event in root.xpath('event'):
            RoadEvent.objects.update_or_create_from_xml(event, **opts)

test_endpoint = TestEndpointView.as_view()


def execute_test_endpoint_command(command, **kwargs):
    class DummyRequest(object):
        pass
    request = DummyRequest()
    request.POST = dict(kwargs)
    request.POST['command'] = command
    return TestEndpointView().post(request)
