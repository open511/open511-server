from functools import partial

from django.http import Http404

from lxml.builder import E

from open511.server.models import Camera
from open511.server.utils.views import APIView, Resource
from open511.server.views import CommonFilters, CommonListView

class CameraListView(CommonListView):

    model = Camera

    resource_name_plural = 'cameras'

    filters = {
        'bbox': CommonFilters.bbox,
        'jurisdiction': CommonFilters.jurisdiction,
        'road_name': partial(CommonFilters.xpath, 'roads/road/name/text()'),
        'area_id': partial(CommonFilters.xpath, 'areas/area/id/text()'),
        'area_name': partial(CommonFilters.xpath, 'areas/area/name/text()'),
        'geography': None,  # dealt with in post_filter
        'tolerance': None,  # dealt with in post_filter
    }

class CameraView(APIView):

    model = Camera

    def get(self, request, jurisdiction_id, id):
        base_qs = self.model.objects.filter(jurisdiction__id=jurisdiction_id)
        try:
            obj = base_qs.get(id=id)
        except Camera.DoesNotExist:
            raise Http404
        return Resource(E.events(obj.to_full_xml_element(
            accept_language=request.accept_language,
        )))

list_cameras = CameraListView.as_view()
camera = CameraView.as_view()