from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin
from django.contrib import admin
from django.contrib.gis.db import models
from django import forms

from open511_server.models import RoadEvent, Jurisdiction, JurisdictionGeography, Area, Camera


class BaseRoadEventForm(forms.BaseModelForm):

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('initial', {})
        if kwargs.get('instance'):
            obj = kwargs['instance']
            for fname, field in self.base_fields.items():
                if hasattr(field, 'get_db_value'):
                    val = field.get_db_value(obj)
                    if val:
                        kwargs['initial'][fname] = val
        super(BaseRoadEventForm, self).__init__(*args, **kwargs)
        print kwargs

    def save(self, commit=True):
        obj = super(BaseRoadEventForm, self).save(commit=False)
        for fname, field in self.base_fields.items():
            if hasattr(field, 'set_db_value'):
                val = self.cleaned_data[fname]
                field.set_db_value(obj, val)
        if commit:
            obj.save()
        return obj

    class Meta(object):
        model = RoadEvent
        exclude = ['xml_data']

class RoadEventAdmin(admin.ModelAdmin):
    list_display = ['headline', 'full_id', 'severity', 'active', 'has_remaining_periods']
    list_filter = ['jurisdiction', 'active']
    search_fields = ['xml_data', 'id']


class JurisdictionAdmin(admin.ModelAdmin):
    filter_horizontal = ['permitted_users']

class JurisdictionGeographyAdmin(admin.ModelAdmin):
    formfield_overrides = {
        models.GeometryField: {'widget': forms.widgets.Textarea }
    }

admin.site.register(RoadEvent, RoadEventAdmin)
admin.site.register(Jurisdiction, JurisdictionAdmin)
admin.site.register(JurisdictionGeography, JurisdictionGeographyAdmin)
admin.site.register(Area)
admin.site.register(Camera)

class JurInline(admin.TabularInline):
    model = Jurisdiction.permitted_users.through
    extra = 1

class CustomUserAdmin(UserAdmin):
    inlines = [JurInline]

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
