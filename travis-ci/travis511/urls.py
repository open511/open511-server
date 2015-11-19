from django.conf.urls import include, url
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib.gis import admin
admin.autodiscover()

urlpatterns = [
    url(r'^admin/', include(admin.site.urls)),
    url(r'^api/', include('open511_server.urls')),
]

urlpatterns += staticfiles_urlpatterns()
