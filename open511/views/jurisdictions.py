from django.shortcuts import get_object_or_404

from open511.models import Jurisdiction
from open511.utils.views import ModelListAPIView, APIView, Resource

class JurisdictionListView(ModelListAPIView):

    allow_jsonp = True
    model = Jurisdiction

    def get_qs(self, request):
        return Jurisdiction.objects.all()

    def object_to_xml(self, request, obj):
        return obj.to_full_xml_element(accept_language=request.accept_language)


class JurisdictionView(APIView):

    model = Jurisdiction

    def get(self, request, slug):
        jur = get_object_or_404(Jurisdiction, slug=slug)
        return Resource(jur.to_full_xml_element(accept_language=request.accept_language))

list_jurisdictions = JurisdictionListView.as_view()
jurisdiction = JurisdictionView.as_view()        