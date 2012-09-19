from django.conf.urls import *

urlpatterns = patterns('open511.views',
    url(r'^events/$', 'list_roadevents'),
    url(r'^events/(?P<jurisdiction_slug>[a-z0-9-]+)/$', 'list_roadevents'),
    url(r'^events/(?P<jurisdiction_slug>[a-z0-9-]+)/(?P<id>[^/]+)/$', 'roadevent',
    	name='open511_roadevent'),
    url(r'^jurisdictions/$', 'list_jurisdictions'),
    url(r'^jurisdictions/(?P<slug>[a-z0-9-]+)/$', 'jurisdiction', name='open511_jurisdiction'),
)