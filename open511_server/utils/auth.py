from open511_server.conf import settings

def can(request, permission):
    """Is this request allowed the given permission?

    permission is a string label"""
    # Currently a dummy implementation that just delegates to django auth
    return settings.OPEN511_ALLOW_EDITING and request.user.is_authenticated()