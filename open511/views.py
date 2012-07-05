from open511.models import RoadEvent
from open511.utils.language import accept_language_from_request
from open511.utils.views import JSONView


class RoadEventListView(JSONView):

    allow_jsonp = True

    def get(self, request):
        accept = accept_language_from_request(request)
        return [
            rdev.to_json_structure(accept=accept) for rdev in RoadEvent.objects.all()
        ]

list_roadevents = RoadEventListView.as_view()
