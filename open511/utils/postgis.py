from django.db import connection, transaction
from django.db.utils import DatabaseError


@transaction.commit_manually
def _convert_gml(gml_string, output_func, force_2D=True):
    sql = 'ST_GeomFromGML(%s)'
    if force_2D:
        sql = 'ST_Force_2D(%s)' % sql
    sql = 'SELECT %s(%s)' % (output_func, sql)

    cursor = connection.cursor()
    try:
        cursor.execute(sql, [gml_string])
        return cursor.fetchone()[0]
    except DatabaseError as e:
        transaction.rollback()
        if 'invalid GML' in unicode(e):
            raise ValueError("Invalid GML: %s" % gml_string)
        raise
    finally:
        transaction.rollback()


def gml_to_ewkt(gml_string, force_2D=True):
    return _convert_gml(gml_string, 'ST_AsEWKT', force_2D=force_2D)


def pg_gml_to_geojson(gml_string):
    return _convert_gml(gml_string, 'ST_AsGeoJSON')
