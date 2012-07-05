from django.contrib.gis import admin

from open511.models import RoadEvent

class RoadEventAdmin(admin.OSMGeoAdmin):
    #list_display = ['title', 'jurisdiction', 'start_date', 'end_date']
    #list_filter = ['jurisdiction', 'start_date', 'end_date']
    pass
    
admin.site.register(RoadEvent, RoadEventAdmin)