import functools

from django.conf import settings
from django.contrib.admin.widgets import AdminDateWidget
from django.contrib.gis import admin
from django import forms
from django.forms.models import ModelFormOptions
from django.utils.datastructures import SortedDict
from django.utils.translation import string_concat

from webob.acceptparse import AcceptLanguage

from open511.models import RoadEvent, Jurisdiction
from open511.utils.serialization import ELEMENTS


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

class RoadEventAdmin(admin.OSMGeoAdmin):
    list_display = ['headline', 'jurisdiction']
    list_filter = ['jurisdiction']
    search_fields = ['xml_data']


# class RoadEventAdmin(admin.OSMGeoAdmin):
#     list_display = ['headline', 'jurisdiction']
#     #list_filter = ['jurisdiction', 'start_date', 'end_date']
#     #form = get_form()

#     def _get_xml_fields(self):
#         fields = SortedDict()
#         MULTILING = len(settings.LANGUAGES) > 1

#         def _tag_getter(tag, obj):
#             try:
#                 return obj.xml_elem.xpath(tag + '/text()')[0]
#             except IndexError:
#                 pass

#         def _tag_setter(tag, obj, val):
#             obj.set_tag_value(tag, val)

#         def _lang_getter(tag, lang, obj):
#             return obj.get_text_value(tag, AcceptLanguage(lang))

#         def _lang_setter(tag, lang, obj, val):
#             return obj.set_text_value(tag, val, lang=lang)

#         for el in ELEMENTS:
#             if el.type == 'TEXT':
#                 for langcode, langname in settings.LANGUAGES:
#                     label = el.name
#                     if MULTILING:
#                         label = string_concat(label, u' (%s)' % langname)
#                     field = forms.CharField(
#                         label=label,
#                         widget=forms.Textarea,
#                         required=False)
#                     field.get_db_value = functools.partial(_lang_getter, el.tag, langcode)
#                     field.set_db_value = functools.partial(_lang_setter, el.tag, langcode)
#                     fields[el.tag + '_' + langcode] = field
#             else:
#                 if el.type == 'CHAR':
#                     field = forms.CharField(label=el.name, required=False)
#                 elif el.type == 'DATE':
#                     field = forms.DateField(label=el.name, widget=AdminDateWidget, required=False)
#                 field.get_db_value = functools.partial(_tag_getter, el.tag)
#                 field.set_db_value = functools.partial(_tag_setter, el.tag)
#                 fields[el.tag] = field
#         return fields

#     def get_form(self, request, obj=None, **kwargs):
#         fields = self._get_xml_fields()

#         for dbfield in RoadEvent._meta.fields:
#             if dbfield.attname in ['jurisdiction', 'geom']:
#                 fields[dbfield.attname] = self.formfield_for_dbfield(dbfield)

#         cls = type('RoadEventForm', (BaseRoadEventForm,), {'base_fields': fields})
#         cls._meta = ModelFormOptions(BaseRoadEventForm.Meta)
#         return cls

admin.site.register(RoadEvent, RoadEventAdmin)
admin.site.register(Jurisdiction)
