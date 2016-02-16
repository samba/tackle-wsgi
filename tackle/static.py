#!/usr/bin/env python

import os
import hashlib
import datetime

from webob import Response, Request
from middleware import middleware
# from wsgi import logger

def md5(*text):
    val = hashlib.md5(text[0])
    for m in text[1:]:
        val.update(m)
    return val.hexdigest()


def capture_response(app, environ):
    request = (environ if isinstance(environ, Request) else Request(environ))
    return request.get_response(app)



class StoredResponse(Response):
    """Load/save responses from/to local storage.

        - Use StoredResponse.from_file(fp) to load; a class method.
        - Use StoredResponse().to_file(fp) to save; an instance method.
    """

    def to_file(self, fp):
        fp.write('HTTP/1.1 %s\n' % self.status)
        if ('Content-Length' not in self.headerlist):
            self.headers['Content-Length'] = str(len(self.body))
        for k, v in self.headerlist:
            fp.write('%s: %s\n' % (k, v))
        fp.write('\n')
        fp.write(self.body)
        fp.write('\n\n')

    @classmethod
    def patch(cls, instance):
        if isinstance(instance, Response):
            class _derived_(cls, instance.__class__):
                pass
            instance.__class__ = _derived_
        return instance

    @classmethod
    def intercept(cls, app, environ):
        return cls.patch(capture_response(app, environ))



class UTC(datetime.tzinfo):

    ZERO = datetime.timedelta(0)

    def utcoffset(self, dt):
        return self.ZERO

    def tzname(self, dt):
        return 'UTC'

    def dst(self, dt):
        return self.ZERO


class StaticCacheMiddleware(object):

    def __init__(self, cachepath=('.static', 'cache'), ttl=3600):

        if isinstance(cachepath, (list, tuple)):
            cachepath = os.path.join(*cachepath)

        self.pool = os.path.join(os.getcwd(), cachepath)
        self.ttl_default = ttl

        try:
            os.makedirs(self.pool)
        except OSError, e:
            pass

    @middleware
    def __call__(self, *args, **kwargs):
        return self.wsgi(*args, **kwargs)


    def generate_path(self, request):
        method = request.method.lower()
        ident = md5(request.path_qs,
                    str(request.accept),
                    str(request.accept_language),
                    str(request.accept_encoding))
        return os.path.join(self.pool, '%s.%s' % (ident, method))

    def wsgi(self, req, app):
        if req.method not in ('HEAD', 'GET'):
            return app

        source_file = self.generate_path(req)
        response = None
        now = datetime.datetime.now(UTC())

        if os.path.isfile(source_file):
            response = StoredResponse.from_file(open(source_file, 'rb'))
            expired = (response.expires < now)
            if expired:  # cache has expired, so reset.
                response = None
            else:
                return response

        if response is None:  # the cache was either not found, or invalid.
            response = StoredResponse.intercept(app, req)

            # Only cache valid resource responses (200)
            if response.status_int in (200,):
                response.last_modified = response.last_modified or now
                if not response.expires:

                    if callable(self.ttl_default):
                        ttl = self.ttl_default(req)
                    else:
                        ttl = self.ttl_default
                    response.cache_expires = ttl

                if response.expires:  # don't cache content lacking expiration
                    response.to_file(open(source_file, 'wb'))

        return response




