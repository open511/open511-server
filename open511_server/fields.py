from django.core.exceptions import FieldError
from django.db import models

class XMLField(models.TextField):

    _south_introspects = True

    def db_type(self, connection):
        engine = connection.settings_dict['ENGINE']
        if 'psycopg2' not in engine and 'postgis' not in engine:
            raise FieldError("XMLField currently implemented only for Postgres")
        return 'xml'
