from django.db import connection

def gml_to_ewkt(gml_string, force_2D=False):
    cursor = connection.cursor()
    if force_2D:
        sql = 'SELECT ST_AsEWKT(ST_Force_2D(ST_GeomFromGML(%s)))'
    else:
        sql = 'SELECT ST_AsEWKT(ST_GeomFromGML(%s))'
    cursor.execute(sql, [gml_string])
    return cursor.fetchone()[0]