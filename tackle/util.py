import threading


class cached_property(object):
    """A decorator that converts a function into a lazy property.

    The function wrapped is called the first time to retrieve the result
    and then that calculated result is used the next time you access
    the value::

        class Foo(object):

            @cached_property
            def foo(self):
                # calculate something important here
                return 42

    The class has to have a `__dict__` in order for this property to
    work.

    .. note:: Implementation detail: this property is implemented as non-data
       descriptor.  non-data descriptors are only invoked if there is
       no entry with the same name in the instance's __dict__.
       this allows us to completely get rid of the access function call
       overhead.  If one choses to invoke __get__ by hand the property
       will still work as expected because the lookup logic is replicated
       in __get__ for manual invocation.

    This class was ported from `Werkzeug`_ and `Flask`_.
    NB: this class was copied from `webapp-improved`_, under an Apache license.
    """

    _default_value = object()

    def __init__(self, func, name=None, doc=None):
        self.__name__ = name or func.__name__
        self.__module__ = func.__module__
        self.__doc__ = doc or func.__doc__
        self.func = func
        self.lock = threading.RLock()

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        with self.lock:
            value = obj.__dict__.get(self.__name__, self._default_value)
            if value is self._default_value:
                value = self.func(obj)
                obj.__dict__[self.__name__] = value

            return value


def apply_middleware(target, *methods):
    """Integrate other middleware components per the basic WSGI convention.

        Common format:

            @middleware3
            @middleware2
            @middleware_decorator(..args...)
            def handler(environ, start_response):
                pass

        Where the decorator convention can't be sensibly applied, this lets us
        integrate a sequence of them nonetheless:

            # a decorator here would raise SyntaxError
            app = WSGIApplication(...)

            app = apply_middleware(
                app,
                middleware_decorator(...args...),  # receives app
                middleware2, # receives middleware_decorator(app)
                middleware3, # receives middleware2(...)
                ...
            )

        effectively applying middleware in the reverse of decorator style.

    """
    for m in methods:
        target = m(target)
    return target


def middleware_aggregate(*methods):
    """Apply a collection of preconfigured middleware.
        Useful when the same collection of middlewares are applied in several
        handlers, etc.

        Usage

            middleware_aggregate()

    """
    def _apply(app):
        return apply_middleware(app, *methods)
    return _apply
