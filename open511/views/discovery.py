from django.core import urlresolvers

from lxml.builder import E

from open511.models import Jurisdiction, RoadEvent, Camera, Area
from open511.utils.serialization import make_link
from open511.utils.views import APIView, Resource

# This should eventually be turned into an autodiscovery of some kind
SERVICES = [
    {
        'type_url': 'http://open511.org/services/events/',
        'description': 'Provide information about events impacting the road system',
        'url_name': 'open511_roadevent_list',
        'test': lambda: RoadEvent.objects.all().exists()
    },
    {
        'type_url': 'http://open511.org/services/areas/',
        'url_name': 'open511_area_list',
        'test': lambda: Area.objects.all().exists()
    },
    {
        'type_url': 'http://open511.org/services/cameras/',
        'url_name': 'open511_camera_list',
        'test': lambda: Camera.objects.all().exists()
    }
]

class DiscoveryView(APIView):

    include_up_link = False
    resource_name = 'discovery'

    def get(self, request):
        jurisdictions = E.jurisdictions(*[
            E.jurisdiction(
                *([E.id(jur.id)] + jur.xml_elem.xpath('name') + 
                [make_link('self', jur.url)])
            ) for jur in Jurisdiction.objects.all()
        ])

        services = E.services(*[
            E.service(
                #E.service_description(s['description']),
                make_link('self', urlresolvers.reverse(s['url_name'])),
                make_link('service_type', s['type_url'])
            ) for s in SERVICES if s['test']()
        ])

        return Resource([jurisdictions, services])

discovery = DiscoveryView.as_view()
