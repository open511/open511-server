from django.conf import settings

class APIPaginator(object):
    """
    Largely cribbed from django-tastypie.
    """
    def __init__(self, request, objects, limit=None, offset=0, max_limit=500):
        """
        Instantiates the ``Paginator`` and allows for some configuration.

        The ``objects`` should be a list-like object of ``Resources``.
        This is typically a ``QuerySet`` but can be anything that
        implements slicing. Required.

        Optionally accepts a ``limit`` argument, which specifies how many
        items to show at a time. Defaults to ``None``, which is no limit.

        Optionally accepts an ``offset`` argument, which specifies where in
        the ``objects`` to start displaying results from. Defaults to 0.
        """
        self.request_data = request.GET
        self.objects = objects
        self.limit = limit
        self.max_limit = max_limit
        self.offset = offset
        self.resource_uri = request.path

    def get_limit(self):
        """
        Determines the proper maximum number of results to return.

        In order of importance, it will use:

            * The user-requested ``limit`` from the GET parameters, if specified.
            * The object-level ``limit`` if specified.
            * ``settings.API_LIMIT_PER_PAGE`` if specified.

        Default is 20 per page.
        """
        settings_limit = getattr(settings, 'API_LIMIT_PER_PAGE', 20)

        if 'limit' in self.request_data:
            limit = self.request_data['limit']
        elif self.limit is not None:
            limit = self.limit
        else:
            limit = settings_limit

        try:
            limit = int(limit)
        except ValueError:
            raise BadRequest("Invalid limit '%s' provided. Please provide a positive integer." % limit)

        if limit == 0:
            if self.limit:
                limit = self.limit
            else:
                limit = settings_limit

        if limit < 0:
            raise BadRequest("Invalid limit '%s' provided. Please provide a positive integer >= 0." % limit)

        if self.max_limit and limit > self.max_limit:
            return self.max_limit

        return limit

    def get_offset(self):
        """
        Determines the proper starting offset of results to return.

        It attempst to use the user-provided ``offset`` from the GET parameters,
        if specified. Otherwise, it falls back to the object-level ``offset``.

        Default is 0.
        """
        offset = self.offset

        if 'offset' in self.request_data:
            offset = self.request_data['offset']

        try:
            offset = int(offset)
        except ValueError:
            raise BadRequest("Invalid offset '%s' provided. Please provide an integer." % offset)

        if offset < 0:
            raise BadRequest("Invalid offset '%s' provided. Please provide a positive integer >= 0." % offset)

        return offset

    def _generate_uri(self, limit, offset):
        if self.resource_uri is None:
            return None

        # QueryDict has a urlencode method that can handle multiple values for the same key
        request_params = self.request_data.copy()
        if 'limit' in request_params:
            del request_params['limit']
        if 'offset' in request_params:
            del request_params['offset']
        request_params.update({'limit': limit, 'offset': max(offset, 0)})
        encoded_params = request_params.urlencode()

        return '%s?%s' % (
            self.resource_uri,
            encoded_params
        )

    def page(self):
        """
        Returns a tuple of (objects, page_data), where objects is one page of objects (a list),
        and page_data is a dict of pagination info.
        """
        limit = self.get_limit()
        offset = self.get_offset()

        page_data = {
            'offset': offset,
            'limit': limit,
        }

        # We get one more object than requested, to see if
        # there's a next page.
        objects = list(self.objects[offset:offset + limit + 1])
        if len(objects) > limit:
            objects.pop()
            page_data['next_url'] = self._generate_uri(limit, offset + limit)
        else:
            page_data['next_url'] = None

        page_data['previous_url'] = (self._generate_uri(limit, offset - limit)
            if offset > 0 else None)

        return (objects, page_data)