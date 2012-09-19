from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from open511.models import RoadEvent, Jurisdiction
from open511.utils.views import APIView, Resource, ResourceList


class RoadEventListView(APIView):

    allow_jsonp = True

    def get(self, request, jurisdiction_slug=None):
        qs = RoadEvent.objects.all()
        if jurisdiction_slug:
            jur = get_object_or_404(Jurisdiction, slug=jurisdiction_slug)
            qs = qs.filter(jurisdiction=jur)

        resources = [
            rdev.to_full_xml_element(accept_language=request.accept_language)
            for rdev in qs
        ]
        return ResourceList(resources)


class RoadEventView(APIView):

    def get(self, request, jurisdiction_slug, id):
        rdev = get_object_or_404(RoadEvent, jurisdiction__slug=jurisdiction_slug, id=id)
        return Resource(rdev.to_full_xml_element(accept_language=request.accept_language))


class JurisdictionListView(APIView):

    allow_jsonp = True

    def get(self, request):
        resources = [
            jur.to_full_xml_element(accept_language=request.accept_language)
            for jur in Jurisdiction.objects.all()
        ]
        return ResourceList(resources)


class JurisdictionView(APIView):

    def get(self, request, slug):
        jur = get_object_or_404(Jurisdiction, slug=slug)
        return Resource(jur.to_full_xml_element(accept_language=request.accept_language))


def unimplemented_view(request, *args, **kwargs):
    return HttpResponse('Not yet implemented')

list_roadevents = RoadEventListView.as_view()
roadevent = RoadEventView.as_view()
list_jurisdictions = JurisdictionListView.as_view()
jurisdiction = JurisdictionView.as_view()
