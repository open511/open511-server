def can(request, permission):
    """Is this request allowed the given permission?

    permission is a string label"""
    # Currently a dummy implementation that just delegates to django auth
    return request.user.is_authenticated()