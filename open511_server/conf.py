from django.conf import settings

from appconf import AppConf


class Open511Settings(AppConf):

    ENABLE_TEST_ENDPOINT = False
    DEFAULT_VERSION = 'v1'
    # Even if ALLOW_EDITING is True, users need to be logged in
    # via django auth, and explicitly given edit permissions on a jurisdiction
    ALLOW_EDITING = True

    # Set this to a logging confic dict, and it'll be used in place
    # of the default settings.LOGGING in the import task runner
    IMPORTER_LOGGING = {}

    class Meta:
        prefix = 'OPEN511'
