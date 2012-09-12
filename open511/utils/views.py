import re

from django.conf import settings
from django.core.serializers.json import simplejson as json
from django.http import HttpResponse
from django.views.generic import View

from lxml import etree

from open511.utils.serialization import xml_to_json, get_base_open511_element


class APIView(View):

    allow_jsonp = True

    def dispatch(self, request, *args, **kwargs):
        result = super(APIView, self).dispatch(request, *args, **kwargs)

        if isinstance(result, HttpResponse):
            return result

        pretty = bool(request.GET.get('indent'))

        output_format = 'xml'
        if request.GET.get('format') == 'json':
            # FIXME use Accept headers
            output_format = 'json'

        if output_format == 'xml':
            base = get_base_open511_element(base=settings.OPEN511_BASE_URL)
            if hasattr(result, 'resource'):
                base.append(result.resource)
            elif hasattr(result, 'resource_list'):
                base.extend(result.resource_list)
            return HttpResponse(
                etree.tostring(base, pretty_print=pretty),
                content_type='application/xml')
        elif output_format == 'json':
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

            if settings.DEBUG and 'html' in request.GET:
                resp = HttpResponse('<html><body>' + resp.content + '</body></html>')

            return resp


class Resource(object):

    def __init__(self, resource):
        self.resource = resource


class ResourceList(object):

    def __init__(self, resource_list):
        self.resource_list = resource_list
        # pagination info...
