from webob.acceptparse import AcceptLanguage

from django.conf import settings

DEFAULT_ACCEPT = AcceptLanguage(settings.LANGUAGE_CODE + ', *;q=0.1')


def accept_language_from_request(request):
    if 'accept-language' in request.GET:
        return AcceptLanguage(request.GET['accept-language'])

    if 'HTTP_ACCEPT_LANGUAGE' in request.META:
        return AcceptLanguage(request.META['HTTP_ACCEPT_LANGUAGE'])

    return DEFAULT_ACCEPT
