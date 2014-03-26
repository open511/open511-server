from open511_server.models import Area
from open511_server.utils.views import ModelListAPIView


class AreaListView(ModelListAPIView):

    allow_jsonp = True
    model = Area

    base_qs = Area.objects.defer('geom')

    def get_qs(self, request):
        return self.base_qs.all()

    def object_to_xml(self, request, obj):
        return obj.remove_unnecessary_languages(request.accept_language)


list_areas = AreaListView.as_view()
