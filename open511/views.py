from webob.acceptparse import AcceptLanguage

from open511.models import RoadEvent
from open511.utils.views import JSONView


class RoadEventListView(JSONView):

    allow_jsonp = True

    def get(self, request):
        opts = {}
        if 'HTTP_ACCEPT_LANGUAGE' in request.META:
            opts['accept'] = AcceptLanguage(request.META['HTTP_ACCEPT_LANGUAGE'])
        return [
            rdev.to_json_structure(**opts) for rdev in RoadEvent.objects.all()
        ]

list_roadevents = RoadEventListView.as_view()
