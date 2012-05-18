from django.conf.urls import *

urlpatterns = patterns('open511.views',
    url(r'^roadevents/$', 'list_roadevents'),
)