from django.conf.urls import *

urlpatterns = patterns('open511.views',
    url(r'^events/$', 'events.list_roadevents', name='open511_roadevent_list'),
    url(r'^events/(?P<jurisdiction_slug>[a-z0-9-]+)/$', 'events.list_roadevents',
        name='open511_roadevent_list'),
    url(r'^events/(?P<jurisdiction_slug>[a-z0-9-]+)/(?P<id>[^/]+)/$', 'events.roadevent',
        name='open511_roadevent'),
    url(r'^jurisdictions/$', 'jurisdictions.list_jurisdictions'),
    url(r'^jurisdictions/(?P<slug>[a-z0-9-]+)/$', 'jurisdictions.jurisdiction', name='open511_jurisdiction'),
    url(r'^$', 'discovery.discovery', name='open511_discovery'),
)
