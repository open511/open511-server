from lxml import etree
import json

from django.http import HttpResponse
from django.views.generic import View

from open511.utils.serialization import xml_to_json

class XMLToJSONView(View):

    META_KEYS = ['up_url', 'url', 'last_updated']
    
    def post(self, request):
        root = etree.fromstring(request.body)
        assert root.tag == 'open511', "The root must be an open511 tag"

        # Strip comments
        for el in root.xpath('//comment()'):
            el.getparent().remove(el)

        conv = xml_to_json(root)
        r = {}

        for key in self.META_KEYS:
            if key in conv:
                r.setdefault('meta', {})[key] = conv[key]
                del conv[key]

        paginated = False
        if 'pagination' in conv:
            r['pagination'] = conv['pagination']
            del conv['pagination']
            paginated = True

        if len(conv.keys()) == 1 and not paginated:
            r['content'] = conv[conv.keys()[0]]
        elif len(set(conv.keys())) == 1:
            r['content'] = conv.values()
        else:
            r['content'] = conv

        return HttpResponse(json.dumps(r, indent=4), content_type='application/json')

x2j = XMLToJSONView.as_view()

