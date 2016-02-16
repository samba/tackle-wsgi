#!/usr/bin/env python

import os
import hashlib
import datetime


from webob import Response, Request

from middleware import middleware


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
        for k, v in self.headerlist:
            fp.write('%s: %s\n' % (k, v))
        fp.write('\n')
        fp.write(self.body)

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
        ident = md5(request.path_qs,
                    str(request.accept),
                    str(request.accept_language),
                    str(request.accept_encoding))
        return os.path.join(self.pool, ident)

    def wsgi(self, req, app):
        if req.method not in ('HEAD', 'GET'):
            return app

        source_file = self.generate_path(req)
        response = None
        now = datetime.datetime.now(UTC())

        if os.path.isfile(source_file):
            response = StoredResponse.from_file(open(source_file, 'rb'))
            expired = (response.expires < now)
            if expired:
                response = None

        if response is None:
            response = StoredResponse.intercept(app, req)
            if response.status_int in (200,):
                response.last_modified = response.last_modified or now
                if not response.expires:
                    response.cache_expires = self.ttl_default
                response.to_file(open(source_file, 'wb'))

        return response




