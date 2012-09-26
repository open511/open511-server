import re

from django.conf import settings
from django.core.serializers.json import simplejson as json
from django.http import HttpResponse
from django.template import loader, RequestContext
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.views.generic import View

from lxml import etree
from lxml.builder import E
from tastypie.paginator import Paginator

from open511.utils.http import accept_from_request, accept_language_from_request
from open511.utils.serialization import xml_to_json, get_base_open511_element, ATOM_LINK


class APIView(View):

    allow_jsonp = True

    potential_response_formats = ['application/xml', 'application/json', 'text/html']

    def determine_response_format(self, request):
        accept = accept_from_request(request)
        return accept.best_match(self.potential_response_formats)

    def determine_accept_language(self, request):
        if request.response_format == 'application/xml':
            # If we're outputting XML, don't prune languages by default
            return accept_language_from_request(request, default=None)
        else:
            return accept_language_from_request(request)

    def dispatch(self, request, *args, **kwargs):

        request.pretty_print = bool(request.GET.get('indent'))
        request.response_format = self.determine_response_format(request)
        request.html_response = (request.response_format == 'text/html')
        if request.html_response:
            request.response_format = 'application/xml'
            request.pretty_print = True

        request.accept_language = self.determine_accept_language(request)

        result = super(APIView, self).dispatch(request, *args, **kwargs)

        if isinstance(result, HttpResponse):
            return result

        if request.response_format == 'application/xml':
            resp = self.render_xml(request, result)
        elif request.response_format == 'application/json':
            resp = self.render_json(request, result)

        if request.html_response:
            resp = self.render_api_browser(request, resp.content)

        return resp

    def render_xml(self, request, result):
        base = get_base_open511_element(base=settings.OPEN511_BASE_URL)
        if hasattr(result, 'resource'):
            base.append(result.resource)
        elif hasattr(result, 'resource_list'):
            base.extend(result.resource_list)
            if getattr(result, 'pagination', None):
                base.append(result.pagination_to_xml())
        return HttpResponse(
            etree.tostring(base, pretty_print=request.pretty_print),
            content_type='application/xml')

    def render_json(self, request, result):
        resp = HttpResponse(content_type='application/json')
        resp_content = {
            'status': 'ok'
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
        t = loader.get_template('open511/api/base.html')

        response_content = escape(response_content)

        # Don't show ampersand escapes
        response_content = response_content.replace('&amp;amp;', '&amp;')
        
        # URLify links
        response_content = re.sub(r'href=&quot;(.+?)&quot;',
            r'href=&quot;<a href="\1">\1</a>&quot;',
            response_content)

        c = RequestContext(request, {
            'response_content': mark_safe(response_content)
        })
        return HttpResponse(t.render(c))


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

        for filt, value in request.GET.items():
            filter_name, x, filter_type = filt.partition('__')
            if filter_name in self.filters:
                qs = self.filters[filter_name](qs, filter_type, value)

        paginator = Paginator(request.GET, qs, resource_uri=request.path)

        page = paginator.page()
        page['meta']['totalCount'] = page['meta']['total_count']
        del page['meta']['total_count']

        return ResourceList(
            [self.object_to_xml(request, o) for o in page['objects']],
            page['meta']
        )


class Resource(object):

    def __init__(self, resource):
        self.resource = resource


class ResourceList(object):

    def __init__(self, resource_list, pagination=None):
        self.resource_list = resource_list
        self.pagination = pagination

    def pagination_to_xml(self):
        el = E.pagination(
            E.totalCount(unicode(self.pagination['totalCount'])),
            E.offset(unicode(self.pagination['offset'])),
            E.limit(unicode(self.pagination['limit'])),
        )
        for linkname in ['previous', 'next']:
            url = self.pagination.get(linkname)
            if url:
                link = etree.Element(ATOM_LINK)
                link.set('rel', linkname)
                link.set('href', url)
                el.append(link)
        return el

