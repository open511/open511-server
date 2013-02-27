import json
import re
import urlparse

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader, RequestContext
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.views.generic import View

from lxml import etree
from lxml.builder import E

from open511.utils.http import accept_from_request, accept_language_from_request
from open511.utils.pagination import APIPaginator
from open511.utils.serialization import xml_to_json, get_base_open511_element, make_link

FORMAT_TO_MIMETYPE = {
    'xml': 'application/xml',
    'json': 'application/json'
}


class APIView(View):

    allow_jsonp = True

    potential_formats = ['xml', 'json']
    potential_versions = ['v0']
    unauthenticated_methods = ('GET', 'HEAD', 'OPTIONS')
    http_method_names = View.http_method_names + ['patch']

    include_up_link = True

    def list_available_media_types(self, include_standard=True):
        types = {}
        if include_standard:
            default_version = self.potential_versions[0]
            for f in self.potential_formats:
                types[FORMAT_TO_MIMETYPE[f]] = (default_version, f)
            types['text/html'] = (default_version, 'html')
        for v in self.potential_versions:
            base = 'application/vnd.open511.' + v
            for f in self.potential_formats:
                types[base + '+' + f] = (v, f)
        return types

    def determine_response_format(self, request):
        """Given a request, returns a tuple of (version, format),
        where format is e.g. 'xml' or 'json'."""
        accept = accept_from_request(request)
        if not getattr(self, '_available_types', None):
            self._available_types = self.list_available_media_types()
        best_type = accept.best_match(self._available_types.keys(),
            default_match='application/xml')
        return self._available_types[best_type]

    def determine_accept_language(self, request):
        if request.response_format == 'xml':
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
        request.response_version, request.response_format = self.determine_response_format(request)
        request.html_response = (request.response_format == 'html')
        if request.html_response:
            if request.COOKIES.get('open511_browser_format') == 'json':
                request.response_format = 'json'
            else:
                request.response_format = 'xml'
            request.pretty_print = True

        request.accept_language = self.determine_accept_language(request)

        result = super(APIView, self).dispatch(request, *args, **kwargs)

        if isinstance(result, HttpResponse):
            return result

        if request.response_format == 'xml':
            resp = self.render_xml(request, result)
        elif request.response_format == 'json':
            resp = self.render_json(request, result)

        if request.html_response:
            resp = self.render_api_browser(request, resp.content)

        resp['X-Open511-Media-Type'] = 'application/vnd.open511.%s+%s' % (request.response_version, request.response_format)

        return resp

    def render_xml(self, request, result):
        base = get_base_open511_element(base=settings.OPEN511_BASE_URL)
        if hasattr(result, 'resource'):
            if isinstance(result.resource, (list, tuple)):
                base.extend(result.resource)
            else:
                base.append(result.resource)
        elif hasattr(result, 'resource_list'):
            base.extend(result.resource_list)
            if getattr(result, 'pagination', None):
                base.append(result.pagination_to_xml())
        metadata = self.get_response_metadata(request)
        base.set('version', metadata['version'])
        base.append(make_link('self', metadata['url']))
        if 'up_url' in metadata:
            base.append(make_link('up', metadata['up_url']))
        return HttpResponse(
            etree.tostring(base, pretty_print=request.pretty_print),
            content_type='application/xml')

    def render_json(self, request, result):
        resp = HttpResponse(content_type='application/json')
        resp_content = {
            'meta': self.get_response_metadata(request)
        }
        if hasattr(result, 'resource'):
            resp_content['content'] = xml_to_json(result.resource)
        elif hasattr(result, 'resource_list'):
            resp_content['content'] = [xml_to_json(r) for r in result.resource_list]
            if getattr(result, 'pagination', None):
                resp_content['pagination'] = result.pagination
        callback = ''
        if self.allow_jsonp and 'callback' in request.GET:
            callback = re.sub(r'[^a-zA-Z0-9_]', '', request.GET['callback'])
            resp.write(callback + '(')
        json.dump(resp_content, resp,
            indent=4 if request.pretty_print else None)
        if callback:
            resp.write(');')
        return resp

    def render_api_browser(self, request, response_content):
        response_content = escape(response_content)

        # Don't show ampersand escapes
        response_content = response_content.replace('&amp;amp;', '&amp;')
        
        # URLify links
        if request.response_format == 'xml':
            response_content = re.sub(r'href=&quot;(.+?)&quot;',
                r'href=&quot;<a href="\1">\1</a>&quot;',
                response_content)
        elif request.response_format == 'json':
            response_content = re.sub(r'(&quot;|_)url&quot;: &quot;(\S+)(&quot;,?\s*\n)',
                r'\1url&quot;: &quot;<a href="\2">\2</a>\3',
                response_content)

        ctx = {
            'response_format': request.response_format,
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
        m = {
            'version': request.response_version,
            'url': request.path, # FIXME query
        }
        if self.include_up_link:
            m['up_url'] = urlparse.urljoin(request.path, '../')
        return m


class ModelListAPIView(APIView):

    # Subclasses should implement:
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

        return ResourceList(
            [self.object_to_xml(request, o) for o in objects],
            pagination
        )

    def post_filter(self, request, qs):
        return qs


class Resource(object):

    def __init__(self, resource):
        self.resource = resource


class ResourceList(object):

    def __init__(self, resource_list, pagination=None):
        self.resource_list = resource_list
        self.pagination = pagination

    def pagination_to_xml(self):
        el = E.pagination(
            #E.totalCount(unicode(self.pagination['totalCount'])),
            E.offset(unicode(self.pagination['offset'])),
            E.limit(unicode(self.pagination['limit'])),
        )
        for linkname in ['previous_url', 'next_url']:
            url = self.pagination.get(linkname)
            if url:
                el.append(make_link(linkname.replace('_url', ''), url))
        return el

