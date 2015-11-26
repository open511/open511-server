from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib.gis.db import models
from django import forms

from open511_server.models import (RoadEvent, Jurisdiction,
    JurisdictionGeography, Area, Camera, ImportTaskStatus)

class RoadEventAdmin(admin.ModelAdmin):
    list_display = ['headline', 'full_id', 'severity', 'active', 'has_remaining_periods']
    list_filter = ['jurisdiction', 'active']
    search_fields = ['xml_data', 'id']


class JurisdictionAdmin(admin.ModelAdmin):
    filter_horizontal = ['permitted_users']

class JurisdictionGeographyAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.GeometryField: {'widget': forms.widgets.Textarea}
    }

class ImportTaskStatusAdmin(admin.ModelAdmin):
    list_display = ['id', 'updated', 'admin_num_imported']

admin.site.register(RoadEvent, RoadEventAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(JurisdictionGeography, JurisdictionGeographyAdmin)
admin.site.register(Area)
admin.site.register(Camera)
admin.site.register(ImportTaskStatus, ImportTaskStatusAdmin)

class JurInline(admin.TabularInline):
    model = Jurisdiction.permitted_users.through
    extra = 1

class CustomUserAdmin(UserAdmin):
    inlines = [JurInline]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
