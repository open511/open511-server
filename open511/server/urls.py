from django.conf.urls import *
from open511.server.conf import settings

urlpatterns = patterns('open511.server.views',
    url(r'^events/$', 'events.list_roadevents', name='open511_roadevent_list'),
    url(r'^events/(?P<jurisdiction_id>[a-z0-9.-]+)/$', 'events.list_roadevents',
        name='open511_roadevent_list'),
    url(r'^events/(?P<jurisdiction_id>[a-z0-9.-]+)/(?P<id>[^/]+)/$', 'events.roadevent',
        name='open511_roadevent'),
    #url(r'^jurisdictions/$', 'jurisdictions.list_jurisdictions'),
    url(r'^jurisdictions/(?P<id>[a-z0-9.-]+)/$', 'jurisdictions.jurisdiction', name='open511_jurisdiction'),
    url(r'^jurisdictions/(?P<id>[a-z0-9.-]+)/geography/$', 'jurisdictions.jurisdiction_geography', name='open511_jurisdiction_geography'),
    url(r'^areas/$', 'areas.list_areas', name="open511_area_list"),
    url(r'^cameras/$', 'cameras.list_cameras', name="open511_camera_list"),
    url(r'^cameras/(?P<jurisdiction_id>[a-z0-9.-]+)/(?P<id>[^/]+)/$', 'cameras.camera', name="open511_camera"),
    url(r'^$', 'discovery.discovery', name='open511_discovery'),
)

if settings.DEBUG:
    if settings.OPEN511_ENABLE_TEST_ENDPOINT:
        urlpatterns += patterns('',
            url(r'^_test/$', 'open511.server.views.test_endpoint.test_endpoint', name='open511_api_test_endpoint'),
        )
