from open511.models import RoadEvent
from open511.utils.views import JSONView

class RoadEventListView(JSONView):

    def get(self, request):
        return [
            rdev.to_json_structure() for rdev in RoadEvent.objects.all()
        ]

list_roadevents = RoadEventListView.as_view()

