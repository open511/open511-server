from django.http import HttpResponse
from django.views.generic import View

from lxml import etree

from open511.utils.serialization import XML_LANG

from open511_server.models import Jurisdiction, RoadEvent

class TestEndpointView(View):

    def post(self, request):
        if request.POST['command'] == 'clear':
            self._clear()
        elif request.POST['command'] == 'load':
            self._load_xml(request.POST['xml'])

        return HttpResponse('OK')

    def _clear(self):
        try:
            jur = Jurisdiction.objects.get(id='test.open511.org')
        except Jurisdiction.DoesNotExist:
            jur = Jurisdiction(id='test.open511.org')
        jur.xml_data = """<jurisdiction xmlns:gml="http://www.opengis.net/gml">
            <name xml:lang="en">TEST</name>
            <timezone>America/Montreal</timezone>
            <email>contact@open511.org</email>
            <link rel="geography" href="http://test.open511.org/"/>
            <link rel="license" href="http://test.open511.org/"/>
            </jurisdiction>"""
        jur.save()

        RoadEvent.objects.filter(jurisdiction=jur).delete()

    def _load_xml(self, xml):
        root = etree.fromstring(xml)
        assert root.tag == 'open511'
        opts = {}
        if root.get(XML_LANG):
            opts['default_language'] = root.get(XML_LANG)
        for event in root.xpath('events/event'):
            RoadEvent.objects.update_or_create_from_xml(event, **opts)

def execute_test_endpoint_command(command, **kwargs):
    class DummyRequest(object):
        pass
    request = DummyRequest()
    request.POST = dict(kwargs)
    request.POST['command'] = command
    return TestEndpointView().post(request)
