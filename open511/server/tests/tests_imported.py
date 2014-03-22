#coding: utf8

import logging
import json

from django.core.urlresolvers import reverse
from django.test import TestCase

try:
    from open511.api_tests.base import set_options as set_external_test_options
    set_external_test_options(
        api_url=reverse('open511_discovery'),
        test_endpoint_url=None,
        use_django_test_client=True
    )
    from open511.api_tests import *
except ImportError:
    logging.warning("Could not import tests from the open511-api-tests package. Perhaps you need to install it?")


# class MultilingualTest(TestCase):
#     fixtures = ['five.json']

#     def test_language_headers(self):
#         url = '/roadevents/'

#         def get(accept_string):
#             req = self.client.get(url, HTTP_ACCEPT_LANGUAGE=accept_string)
#             return json.loads(req.content)

#         def titles(resp):
#             return [r['Title'] for r in resp['content'] if r.get('Title')]

#         # If we ask for Chinese, we should get nothing
#         self.assertEqual(len(titles(get('zh'))), 0)

#         # If we ask for Chinese or whatever, we should get five
#         assert len(titles(get('zh, *;q=0.1'))) == 5

#         # If we ask for English, we should get only one
#         eng = titles(get('en'))
#         assert len(eng) == 1

#         # If we ask for French, we should get five in French
#         fr = titles(get('fr'))
#         assert len(fr) == 5
#         assert u"Réfection d'infrastructures souterraines" in fr

#         # If we ask for French or whatever, we should get five in French
#         assert fr == titles(get('fr-fr, en;q=0.9, *;q=0.5'))

#         # If we ask for English then French, we should get just that
#         enfr = titles(get('en-ca, fr;q=0.9'))
#         assert len(enfr) == 5
#         assert u"Underground infrastructure repair" in enfr
#         assert u"Réfection d'infrastructures souterraines" not in enfr
