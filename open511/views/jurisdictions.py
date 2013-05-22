from django.shortcuts import get_object_or_404

from open511.models import Jurisdiction, JurisdictionGeography
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

    up_url = '../../'

    def get(self, request, slug):
        jur = get_object_or_404(Jurisdiction, slug=slug)
        return Resource(jur.to_full_xml_element(accept_language=request.accept_language))


class JurisdictionGeographyView(APIView):

    model = JurisdictionGeography

    def get(self, request, slug):
        jur_geo = get_object_or_404(JurisdictionGeography, jurisdiction__slug=slug)
        return Resource(jur_geo.to_full_xml_element())

list_jurisdictions = JurisdictionListView.as_view()
jurisdiction = JurisdictionView.as_view()
jurisdiction_geography = JurisdictionGeographyView.as_view()
