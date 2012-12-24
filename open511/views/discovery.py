from django.core import urlresolvers

from lxml.builder import E

from open511.models import Jurisdiction
from open511.utils.serialization import make_link
from open511.utils.views import APIView, Resource

# This should eventually be turned into an autodiscovery of some kind
SERVICES = [
    {
        'type': 'events',
        'description': 'Provide information about events impacting the road system',
        'url_name': 'open511_roadevent_list'
    }
]

class DiscoveryView(APIView):

    include_up_link = False

    def get(self, request):
        jurisdictions = E.jurisdictions(*[
            E.jurisdiction(
                *(jur.xml_elem.xpath('name') + 
                [make_link('self', jur.get_absolute_url())])
            ) for jur in Jurisdiction.objects.all()
        ])

        services = E.services(*[
            E.service(
                E.service_type(s['type']),
                E.service_description(s['description']),
                make_link('self', urlresolvers.reverse(s['url_name']))
            ) for s in SERVICES
        ])

        return Resource([jurisdictions, services])

discovery = DiscoveryView.as_view()
