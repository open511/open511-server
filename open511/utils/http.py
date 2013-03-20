from webob.acceptparse import AcceptLanguage, MIMEAccept

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

try:
    DEFAULT_ACCEPT_LANGUAGE = AcceptLanguage(settings.LANGUAGE_CODE + ', *;q=0.1')
except (ImportError, ImproperlyConfigured):
    DEFAULT_ACCEPT_LANGUAGE = None
DEFAULT_ACCEPT = MIMEAccept('application/xml')


def accept_language_from_request(request, default=DEFAULT_ACCEPT_LANGUAGE):
    if 'accept-language' in request.GET:
        return AcceptLanguage(request.GET['accept-language'])

    if 'HTTP_ACCEPT_LANGUAGE' in request.META:
        return AcceptLanguage(request.META['HTTP_ACCEPT_LANGUAGE'])

    return default


def accept_from_request(request, default=DEFAULT_ACCEPT):

    if 'format' in request.GET:
        if request.GET['format'] == 'xml':
            return MIMEAccept('application/xml')
        elif request.GET['format'] == 'json':
            return MIMEAccept('application/json')
        return MIMEAccept(request.GET['format'])

    if 'HTTP_ACCEPT' in request.META:
        return MIMEAccept(request.META['HTTP_ACCEPT'])

    return default
