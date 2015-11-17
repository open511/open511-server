from django.shortcuts import get_object_or_404

from lxml.builder import E

from open511_server.models import Jurisdiction, JurisdictionGeography
from open511_server.utils.views import ModelListAPIView, APIView, Resource

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

    def get(self, request, id):
        jur = get_object_or_404(Jurisdiction, id=id)
        return Resource(E.jurisdictions(jur.to_full_xml_element(accept_language=request.accept_language)))


class JurisdictionGeographyView(APIView):

    model = JurisdictionGeography

    def get(self, request, id):
        jur_geo = get_object_or_404(JurisdictionGeography, jurisdiction__id=id)
        return Resource(E.geographies(jur_geo.to_full_xml_element()))
