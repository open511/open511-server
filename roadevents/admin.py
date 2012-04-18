from django.contrib.gis import admin

from roadevents.models import RoadEvent

class RoadEventAdmin(admin.OSMGeoAdmin):
    pass
    
admin.site.register(RoadEvent, RoadEventAdmin)