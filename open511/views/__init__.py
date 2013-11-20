import operator

from django.contrib.gis.geos import Polygon
from django.contrib.gis.measure import Distance
from django.db.models import Q
from django.shortcuts import get_object_or_404

import dateutil.parser

from open511.models import Jurisdiction, SearchGeometry
from open511.utils.views import APIView, ModelListAPIView, Resource

class CommonFilters(object):

    @staticmethod
    def xpath(xpath, qs, value, typecast='text', allow_list=True):
        if allow_list:
            if isinstance(value, basestring):
                value = value.split(',')
        else:
            value = [value]
        return qs.extra(
            where=['(xpath(%s, {0}.xml_data))::{1}[] && %s'.format(qs.model._meta.db_table, typecast)],
            params=[xpath, value]
        )

    @staticmethod
    def db(fieldname, qs, value, allow_operators=False):
        if allow_operators:
            op, value = _parse_operator_from_value(value)
            fieldname = fieldname + '__' + op
        return qs.filter(**{fieldname: value})

    @staticmethod
    def datetime(fieldname, qs, value):
        query_type, value = _parse_operator_from_value(value)
        value = dateutil.parser.parse(value)
        if not value.tzinfo:
            raise ValueError("Time-based filters must provide a timezone")
        return qs.filter(**{'__'.join((fieldname, query_type)): value})

    @staticmethod
    def bbox(qs, value, fieldname='geom'):
        coords = [float(n) for n in value.split(',')]
        assert len(coords) == 4
        return qs.filter(**{fieldname + '__intersects': Polygon.from_bbox(coords)})

    @staticmethod
    def geography(qs, value, within=None):
        search_geom = SearchGeometry.fromstring(value)
        if within is not None:
            return qs.filter(geom__dwithin=(search_geom.geom, Distance(m=within)))
        return qs.filter(geom__intersects=search_geom.geom)

    @staticmethod
    def jurisdiction(qs, value):
        # The jurisdiction parameter can be:
        # - A full http:// URL to the external jurisdiction
        # - Some kind of relative URL: /api/jurisdictions/mtq
        # - Just the ID: ville.montreal.qc.ca
        filters = []
        for jur in value.split(','):
            filters.append(Q(jurisdiction__external_url=jur))
            filters.append(Q(jurisdiction__id=jur.rstrip('/').split('/')[-1]))
        return qs.filter(reduce(operator.or_, filters))

FILTER_OPERATORS = [
    ('<=', 'lte'),
    ('>=', 'gte'),
    ('<', 'lt'),
    ('>', 'gt')
]
def _parse_operator_from_value(value):
    for op, query_type in FILTER_OPERATORS:
        if value.startswith(op):
            return query_type, value[len(op):]
    return 'exact', value

class CommonListView(ModelListAPIView):

    def post_filter(self, request, qs):
        objects = super(CommonListView, self).post_filter(request, qs)
        if 'geography' in request.REQUEST and 'geography' in self.filters:
            objects = CommonFilters.geography(objects, request.REQUEST['geography'],
                within=request.REQUEST.get('tolerance'))  

        return objects

    def get_qs(self, request, jurisdiction_id=None):
        qs = self.model._default_manager.all()
        if jurisdiction_id:
            jur = get_object_or_404(Jurisdiction, id=jurisdiction_id)
            qs = qs.filter(jurisdiction=jur)
        return qs

    def object_to_xml(self, request, obj):
        return obj.to_full_xml_element(
            accept_language=request.accept_language,
        )        