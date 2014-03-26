import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()

def jsonfilter(value):
    return mark_safe(json.dumps(value))

register.filter('json', jsonfilter)

