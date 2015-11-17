from functools import partial
import time

_cached_objects = dict()

CACHE_EXPIRY = 60 * 10
def get_cached_object(model, id):
    """
    A very, very simple in-memory cache for ORM objects.
    No invalidation other than restarting this app or waiting CACHE_EXPIRY seconds.
    """
    lookup = (model, id)
    cached = _cached_objects.get(lookup)
    if cached and cached[0] > time.time():
        return cached[1]

    obj = model.objects.get(pk=id)
    _cached_objects[lookup] = (time.time() + CACHE_EXPIRY, obj)
    return obj

class memoize_method(object):
    """
    Simple memoize decorator for instance methods.
    http://code.activestate.com/recipes/577452-a-memoize-decorator-for-instance-methods/
    """
    def __init__(self, func):
        self.func = func

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self.func
        return partial(self, obj)

    def __call__(self, *args, **kw):
        obj = args[0]
        try:
            cache = obj.__cache
        except AttributeError:
            cache = obj.__cache = {}
        key = (self.func, args[1:], frozenset(kw.items()))
        try:
            res = cache[key]
        except KeyError:
            res = cache[key] = self.func(*args, **kw)
        return res
