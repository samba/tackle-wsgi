# WSGI middleware layers.
# Copyright (c) 2015, Sam Briesemeister
# Licensed under the Python Software Foundation License.


# from tackle.wsgi import sendfile
from tackle.wsgi import RequestInfo
from tackle.wsgi import WSGIRequestHandler
# from tackle.wsgi import apply_middl eware, middleware_aggregate
# from tackle.wsgi import logger
from tackle.util import stripfirst


import re
import urlparse





class Middleware(object):

    @staticmethod
    def prepend_wsgi(handler, downstream, call_app_internally = False):
        def intercept(environ, start_response):
            if call_app_internally:
                result = handler(environ, start_response, downstream)
            else:
                result = handler(environ, start_response)
            if result is not None:
                return result
            else:
                return downstream(environ, start_response)
        return intercept

    @staticmethod
    def append_wsgi(handler, upstream):
        def afterall(environ, start_response):
            uresult = upstream(environ, start_response)
            if uresult is not None:
                uresult = handler(environ, start_response, uresult)
            return uresult
        return afterall


    def __init__(self, *args, **opts):
        self.arguments = args
        self.options = opts

    def __call__(self, wsgi):
        """Integration hook to intercept and attach WSGI middleware, optionally
            as a method decorator.
        """
        app = wsgi
        run_before = getattr(self, 'wsgi_request', None)
        run_after = getattr(self, 'wsgi_response', None)
        run_internal = getattr(self, 'options', {}).pop('internal', False)
        if callable(run_before):
            app = self.prepend_wsgi(run_before, app,
                                    call_app_internally = run_internal)
        if callable(run_after):
            app = self.append_wsgi(run_after, app)
        return app





class RedirectionMiddleware(Middleware):
    """ WSGI Middleware to intercept requests that should be redirected.
        Supports Regular Expressions patterns for extracting parts from
        URLs intercepted, and format strings for target URLs.


        Usage:
            redir = RedirectionMiddleware()
            redir.redirect('^/cdn/(.*)', 'http://cdn.host.com/{1}')
            app = redir.wsgi(upstream_app)

    """


    def __init__(self, _map = None, retain_path = False, retain_query = True):
        # logger.info('middleware_init %r' % self)
        self.retain_path = retain_path
        self.retain_query = retain_query
        self._map = []
        if isinstance(_map, (list, tuple)):
            for m in _map:
                self.redirect(*m)

    def redirect(self, detect, target, permanent = False):
        self._map.append((re.compile(detect), target, permanent))

    def wsgi_request(self, environ, start_response):
        info = RequestInfo(environ)

        status = [ "302 Temporary Redirect", "301 Permanent Redirect" ]

        for pattern, target, permanent in self._map:
            match = pattern.match(info.path)
            if match is not None:
                args, kwargs = match.groups(), match.groupdict()
                parts = list(urlparse.urlsplit(target))
                if self.retain_query:
                    parts[3] = (info.query or parts[3]).lstrip('?')
                if self.retain_path:
                    parts[2] = info.path
                kwargs.update({
                    'hostname': info.hostname,
                    'path': info.path,
                    'query': info.query,
                    'path_qs': info.path_qs
                })
                result = urlparse.urlunsplit(parts).format(*args, **kwargs)
                start_response(status[int(permanent)], [('Location', result)])
                return ['Redirecting to %s' % result]









class Shortener(RedirectionMiddleware):
    """ A simple abstraction for redirection.

        Usage:
            shortener = Shortener(basepath = "/s/")

            # /s/abc => 302 http://abc.com
            shortener.redirect('abc', 'http://abc.com')

    """


    def __init__(self, *args, **kwargs):
        self.basepath = kwargs.pop('basepath', '/')
        super(Shortener, self).__init__(*args, **kwargs)

    def redirect(self, reference, destination_url, permanent = False):
        pattern = self.basepath + reference + '$'
        super(Shortener, self).redirect(pattern, destination_url, permanent)
