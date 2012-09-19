import re

from django.conf import settings
from django.core.serializers.json import simplejson as json
from django.http import HttpResponse
from django.template import loader, RequestContext
from django.template.defaultfilters import escape
from django.utils.safestring import mark_safe
from django.views.generic import View

from lxml import etree

from open511.utils.http import accept_from_request
from open511.utils.serialization import xml_to_json, get_base_open511_element


class APIView(View):

    allow_jsonp = True

    potential_response_formats = ['application/xml', 'application/json', 'text/html']

    def determine_response_format(self, request):
        accept = accept_from_request(request)
        return accept.best_match(self.potential_response_formats)

    def dispatch(self, request, *args, **kwargs):

        pretty = bool(request.GET.get('indent'))


        request.response_format = self.determine_response_format(request)
        request.html_response = (request.response_format == 'text/html')
        if request.html_response:
            request.response_format = 'application/xml'
            pretty = True

        result = super(APIView, self).dispatch(request, *args, **kwargs)

        if isinstance(result, HttpResponse):
            return result


        if request.response_format == 'application/xml':
            base = get_base_open511_element(base=settings.OPEN511_BASE_URL)
            if hasattr(result, 'resource'):
                base.append(result.resource)
            elif hasattr(result, 'resource_list'):
                base.extend(result.resource_list)
            resp = HttpResponse(
                etree.tostring(base, pretty_print=pretty),
                content_type='application/xml')
        elif request.response_format == 'application/json':
            resp = HttpResponse(content_type='application/json')
            if hasattr(result, 'resource'):
                content = xml_to_json(result.resource)
            elif hasattr(result, 'resource_list'):
                content = [xml_to_json(r) for r in result.resource_list]
            callback = ''
            if self.allow_jsonp and 'callback' in request.GET:
                callback = re.sub(r'[^a-zA-Z0-9_]', '', request.GET['callback'])
                resp.write(callback + '(')
            json.dump({
                'status': 'ok',
                'content': content
                }, resp, indent=4 if pretty else None)
            if callback:
                resp.write(');')

        if request.html_response:
            resp = self.render_api_browser(request, resp.content)

        return resp

    def render_api_browser(self, request, response_content):
        t = loader.get_template('open511/api/base.html')

        # URLify links
        response_content = escape(response_content)
        response_content = re.sub(r'href=&quot;(.+?)&quot;',
            r'href=&quot;<a href="\1">\1</a>&quot;',
            response_content)

        c = RequestContext(request, {
            'response_content': mark_safe(response_content)
        })
        return HttpResponse(t.render(c))


class Resource(object):

    def __init__(self, resource):
        self.resource = resource


class ResourceList(object):

    def __init__(self, resource_list):
        self.resource_list = resource_list
        # pagination info...
