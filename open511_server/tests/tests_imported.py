#coding: utf8

import logging

from django.core.urlresolvers import reverse

try:
    from open511_api_tests.base import set_options as set_external_test_options
    set_external_test_options(
        api_url=reverse('open511_discovery'),
        test_endpoint_url=None,
        use_django_test_client=True
    )
    from open511_api_tests import *
except ImportError:
    logging.exception("Could not import tests from the open511-api-tests package. Perhaps you need to install it?")

