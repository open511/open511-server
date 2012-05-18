from django.db import connection, transaction
from django.db.utils import DatabaseError

@transaction.commit_manually
def gml_to_ewkt(gml_string, force_2D=False):
    cursor = connection.cursor()
    if force_2D:
        sql = 'SELECT ST_AsEWKT(ST_Force_2D(ST_GeomFromGML(%s)))'
    else:
        sql = 'SELECT ST_AsEWKT(ST_GeomFromGML(%s))'
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
