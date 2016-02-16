"""WSGI Middlware layers."""

# WSGI middleware layers.
# Copyright (c) 2015, Sam Briesemeister
# Licensed under the Python Software Foundation License.

from webob.dec import wsgify

import re
import urlparse


RE_EMPTY = re.compile(r'^$')


def is_regex(expr):
    return type(RE_EMPTY) is type(expr)


def middleware(handler):
    """Wrap a function to be called with correct binding when WebOb's
        wsgify.middleware hands off a request. The key here is to bind the
        method before wsgify wraps it.
    """
    def method(self, *args, **kwargs):
        method = handler.__get__(self, self.__call__)
        return wsgify.middleware(method, *args, **kwargs)

    return method


class RedirectionMiddleware(object):

    def __init__(self, *routes, **kwargs):
        self.prefix = kwargs.pop('prefix', None)
        if len(routes) and isinstance(routes[0], basestring):
            self.prefix = routes[0]
            routes = list(routes)[1:]
        self.routes = [self.compile_route(*r) for r in routes]
        self.retain_path = kwargs.pop('retain_path', False)
        self.retain_query = kwargs.pop('retain_query', True)

    def compile_route(self, token, target, permanent=False):
        prefix = self.prefix or ''

        if isinstance(token, basestring):
            if not token.startswith('^'):
                token = '^%s%s' % (prefix, token)
            if not token.endswith('$'):
                token = '%s$' % (token)
            pattern = re.compile(token)

        elif is_regex(token):
            pattern = token

        return (pattern, target, permanent)

    def redirect(self, token, target, permanent=False):
        self.routes.append(self.compile_route(token, target, permanent))

    def wsgi(self, req, app):
        path = req.path

        for expr, target, permanent in self.routes:
            match = expr.match(path)
            if match:
                location = match.expand(target)
                parts = list(urlparse.urlsplit(location))

                if self.retain_query:
                    parts[3] = (req.query_string or parts[3]).lstrip('?')
                if self.retain_path:
                    parts[2] = req.path

                location = urlparse.urlunsplit(parts)
                req.response.location = location
                req.response.status = (301 if permanent else 302)
                return req.response

        return app

    @middleware
    def __call__(self, *args, **kwargs):
        return self.wsgi(*args, **kwargs)


class Shortener(RedirectionMiddleware):
    """ A simple abstraction for redirection.

        Usage:
            shortener = Shortener(basepath = "/s/")

            # /s/abc => 302 http://abc.com
            shortener.redirect('abc', 'http://abc.com')

    """
    def __init__(self, *args, **kwargs):
        kwargs['prefix'] = kwargs.pop('basepath', '/')
        super(Shortener, self).__init__(*args, **kwargs)

