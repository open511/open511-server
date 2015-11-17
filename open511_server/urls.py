from django.conf.urls import url
from open511_server.conf import settings

from open511_server.views.events import RoadEventView, RoadEventListView
from open511_server.views.jurisdictions import JurisdictionView, JurisdictionGeographyView
from open511_server.views.cameras import CameraView, CameraListView
from open511_server.views.areas import AreaListView
from open511_server.views.discovery import DiscoveryView
from open511_server.views.test_endpoint import TestEndpointView

urlpatterns = [
    url(r'^events/$', RoadEventListView.as_view(), name='open511_roadevent_list'),
    url(r'^events/(?P<jurisdiction_id>[a-z0-9.-]+)/$', RoadEventListView.as_view(),
        name='open511_roadevent_list'),
    url(r'^events/(?P<jurisdiction_id>[a-z0-9.-]+)/(?P<id>[^/]+)/$', RoadEventView.as_view(),
        name='open511_roadevent'),
    #url(r'^jurisdictions/$', 'jurisdictions.list_jurisdictions'),
    url(r'^jurisdictions/(?P<id>[a-z0-9.-]+)/$', JurisdictionView.as_view(),
        name='open511_jurisdiction'),
    url(r'^jurisdictions/(?P<id>[a-z0-9.-]+)/geography/$', JurisdictionGeographyView.as_view(),
        name='open511_jurisdiction_geography'),
    url(r'^areas/$', AreaListView.as_view(), name="open511_area_list"),
    url(r'^cameras/$', CameraListView.as_view(), name="open511_camera_list"),
    url(r'^cameras/(?P<jurisdiction_id>[a-z0-9.-]+)/(?P<id>[^/]+)/$', CameraView.as_view(),
        name="open511_camera"),
    url(r'^$', DiscoveryView.as_view(), name='open511_discovery'),
]

if settings.DEBUG:
    if settings.OPEN511_ENABLE_TEST_ENDPOINT:
        urlpatterns += [
            url(r'^_test/$', TestEndpointView.as_view(), name='open511_api_test_endpoint'),
        ]
