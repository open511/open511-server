from django.contrib.gis import admin

from open511.models import RoadEvent

class RoadEventAdmin(admin.OSMGeoAdmin):
    pass
    
admin.site.register(RoadEvent, RoadEventAdmin)