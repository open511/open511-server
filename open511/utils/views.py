import json
import re
import time
import urlparse

from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.template.defaultfilters import escape
from django.utils.cache import patch_vary_headers
from django.utils.http import http_date
from django.utils.safestring import mark_safe
from django.views.generic import View

from lxml import etree
from lxml.builder import E

from open511_validator.converter import xml_to_json

from open511.utils.exceptions import BadRequest
from open511.utils.http import accept_from_request, accept_language_from_request
from open511.utils.pagination import APIPaginator
from open511.utils.serialization import get_base_open511_element, make_link

class APIView(View):

    allow_jsonp = True

    potential_content_types = set(('application/xml', 'application/json', 'text/html'))
    potential_versions = [settings.OPEN511_DEFAULT_VERSION]
    unauthenticated_methods = ('GET', 'HEAD', 'OPTIONS')
    http_method_names = View.http_method_names + ['patch']

    include_up_link = True

    def determine_response_format(self, request):
        """Given a request, returns a tuple of (version, format),
        where format is e.g. 'xml' or 'json'."""
        accept = accept_from_request(request)
        return accept.best_match(self.potential_content_types)

    def determine_response_version(self, request):
        if 'version' in request.GET and request.GET['version'] in self.potential_versions:
            return request.GET['version']
        elif 'HTTP_OPEN511_VERSION' in request.META and request.META['HTTP_OPEN511_VERSION'] in self.potential_versions:
            return request.META['HTTP_OPEN511_VERSION']
        return self.potential_versions[0]

    def determine_accept_language(self, request):
        if request.response_format == 'application/xml':
            # If we're outputting XML, don't prune languages by default
            return accept_language_from_request(request, default=None)
        else:
            return accept_language_from_request(request)

    def dispatch(self, request, *args, **kwargs):

        if request.method not in self.unauthenticated_methods and not request.user.is_authenticated():
            resp = HttpResponse("You need to be logged in to do that.", content_type='text/plain')
            resp.status_code = 401
            return resp

        request.pretty_print = bool(request.GET.get('indent'))
        request.response_format = self.determine_response_format(request)
        request.response_version = self.determine_response_version(request)

        request.html_response = (request.response_format == 'text/html')
        if request.html_response:
            if request.COOKIES.get('open511_browser_format') == 'json':
                request.response_format = 'application/json'
            else:
                request.response_format = 'application/xml'
            request.pretty_print = True

        request.accept_language = self.determine_accept_language(request)

        try:
            result = super(APIView, self).dispatch(request, *args, **kwargs)
        except BadRequest as e:
            return HttpResponseBadRequest(unicode(e))

        if isinstance(result, HttpResponse):
            return result

        if request.response_format == 'application/xml':
            resp = self.render_xml(request, result)
        elif request.response_format == 'application/json':
            resp = self.render_json(request, result)

        if request.html_response:
            resp = self.render_api_browser(request, resp.content)

        # Set response headers
        if 'HTTP_ORIGIN' in request.META and request.method == 'GET':
            # Allow cross-domain requests
            resp['Access-Control-Allow-Origin'] = '*'

        if not resp.has_header('Expires'):
            resp['Expires'] = http_date(time.time())

        patch_vary_headers(resp, ['Accept', 'Accept-Language', 'Open511-Version'])

        return resp

    def get_xml_doc(self, request, result):
        base = get_base_open511_element(base=settings.OPEN511_BASE_URL)
        if isinstance(result.resource, (list, tuple)):
            base.extend(result.resource)
        else:
            base.append(result.resource)
        if getattr(result, 'pagination', None):
            base.append(result.pagination_to_xml())
        metadata = self.get_response_metadata(request)
        base.set('version', metadata['version'])
        base.append(make_link('self', metadata['url']))
        if 'up_url' in metadata:
            base.append(make_link('up', metadata['up_url']))
        return base

    def render_xml(self, request, result):
        return HttpResponse(
            etree.tostring(self.get_xml_doc(request, result), pretty_print=request.pretty_print),
            content_type='application/xml')

    def render_json(self, request, result):
        xml_doc = self.get_xml_doc(request, result)
        json_obj = xml_to_json(xml_doc)

        resp = HttpResponse(content_type='application/json')
        callback = ''
        if self.allow_jsonp and 'callback' in request.GET:
            callback = re.sub(r'[^a-zA-Z0-9_]', '', request.GET['callback'])
            resp.write(callback + '(')
        json.dump(json_obj, resp,
            indent=4 if request.pretty_print else None)
        if callback:
            resp.write(');')
        return resp

    def render_api_browser(self, request, response_content):
        response_content = escape(response_content)

        # Don't show ampersand escapes
        response_content = response_content.replace('&amp;amp;', '&amp;')
        
        # URLify links
        if request.response_format == 'application/xml':
            response_content = re.sub(r'href=&quot;(.+?)&quot;',
                r'href=&quot;<a href="\1">\1</a>&quot;',
                response_content)
        elif request.response_format == 'application/json':
            response_content = re.sub(r'(&quot;|_)url&quot;: &quot;(\S+)(&quot;,?\s*\n)',
                r'\1url&quot;: &quot;<a href="\2">\2</a>\3',
                response_content)

        ctx = {
            'response_format': request.response_format.split('/')[1],
            'response_content': mark_safe(response_content),
            'get_params': request.GET.items(),
        }

        if 'accept-language' not in request.GET:
            ctx['get_params'] += [['accept-language', unicode(request.accept_language)]]

        if getattr(self, 'filters', None):
            ctx['available_filters'] = self.filters.keys()

        ctx['is_list'] = isinstance(self, ModelListAPIView)
        model = getattr(self, 'model', None)
        if model:
            ctx['resource_name'] = model._meta.verbose_name
            ctx['resource_name_plural'] = model._meta.verbose_name_plural
        else:
            ctx['resource_name'] = getattr(self, 'resource_name', '')
            ctx['resource_name_plural'] = getattr(self, 'resource_name_plural', '')

        return render(request, "open511/api/base.html", ctx)

    def get_response_metadata(self, request):
        url = request.path
        if request.META.get('QUERY_STRING'):
            url += '?' + request.META['QUERY_STRING']
        m = {
            'version': request.response_version,
            'url': url,
        }
        if self.include_up_link:
            if getattr(self, 'up_url', None):
                m['up_url'] = urlparse.urljoin(request.path, self.up_url)
            else:
                m['up_url'] = urlparse.urljoin(request.path, '../')
        return m


class ModelListAPIView(APIView):

    # Subclasses should implement:
    #
    # model = ModelClass
    #
    # def get_qs(self, request, any_kwargs_from_url):
    #    returns a QuerySet
    #
    # def object_to_xml(self, request, obj):
    #    return object.to_xml()

    filters = {}

    def get(self, request, **kwargs):
        qs = self.get_qs(request, **kwargs)

        for filter_name, value in request.GET.items():
            if self.filters.get(filter_name):
                qs = self.filters[filter_name](qs, value)

        objects = self.post_filter(request, qs)

        paginator = APIPaginator(request, objects)

        objects, pagination = paginator.page()

        if not getattr(self, 'resource_name_plural', None):
            self.resource_name_plural = self.model._meta.verbose_name_plural.lower().replace(' ', '_')

        xml_objects = [self.object_to_xml(request, o) for o in objects]
        el = etree.Element(self.resource_name_plural)
        el.extend(xml_objects)

        return Resource(el, pagination)

    def post_filter(self, request, qs):
        return qs


class Resource(object):

    def __init__(self, resource, pagination=None):
        self.resource = resource
        self.pagination = pagination

    def pagination_to_xml(self):
        if not self.pagination:
            return None
        el = E.pagination(
            E.offset(unicode(self.pagination['offset'])),
        )
        for linkname in ['previous_url', 'next_url']:
            url = self.pagination.get(linkname)
            if url:
                el.append(make_link(linkname.replace('_url', ''), url))
        return el
