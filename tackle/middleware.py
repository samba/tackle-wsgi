# WSGI middleware layers.
# Copyright (c) 2015, Sam Briesemeister
# This code is not yet licensed for redistribution, and no warranty is provided for its use.


from tackle.wsgi import sendfile
from tackle.wsgi import RequestInfo
from tackle.util import stripfirst

import os
import re
import urlparse


class Middleware(object):

    def __init__(self, *args, **options):
        self.arguments = args
        self.options = options

    def run_before(self, environ, start_response):
        pass

    def run_after(self, environ, start_response, result):
        return result

    def wsgi(self, app):
        def __wrapper__(environ, start_response):
            intercept = self.run_before(environ, start_response)
            if not intercept:
                result = app(environ, start_response)
                result = self.run_after(environ, start_response, result)
                return result
            else:
                return intercept
        return __wrapper__

    def __call__(self, environ, start_response):
        intercept = self.run_before(environ, start_response)
        if not intercept:
            result = self.run_after(environ, start_response, intercept)
            return result
        else:
            return intercept



class RedirectionMiddleware(Middleware):
    """ WSGI Middleware to intercept requests that should be redirected.
        Supports Regular Expressions patterns for extracting parts from
        URLs intercepted, and format strings for target URLs.


        Usage:
            redir = RedirectionMiddleware()
            redir.redirect('^/cdn/(.*)', 'http://cdn.host.com/{1}')
            app = redir.wsgi(upstream_app)

    """


    def __init__(self, retain_path = False, retain_query = True):
        self.retain_path = retain_path
        self.retain_query = retain_query
        self._map = []

    def redirect(self, detect, target, permanent = False):
        self._map.append((re.compile(detect), target, permanent))



    def run_before(self, environ, start_response):
        info = RequestInfo(environ)
        status = [ "302 Temporary Redirect", "301 Permanent Redirect" ]

        for pattern, target, permanent in self._map:
            match = pattern.match(info.path)
            if match is not None:
                args, kwargs = match.groups(), match.groupdict()
                parts = list(urlparse.urlsplit(target))
                if self.retain_query:
                    parts[3] = stripfirst('?', info.query)
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
                return 'Redirecting to %s' % result




class StaticFileMiddleware(Middleware):

    default_cache_life = 3600

    match_content_types = [
        (r'\.js$', 'text/javascript', default_cache_life),
        (r'\.json$', 'application/json', default_cache_life),
        (r'\.txt$', 'text/plain', 600),
        (r'\.css$', 'text/css', default_cache_life)
    ]



    def get_headers(self, filename):
        for pattern, content_type, cache_life in self.match_content_types:
            if re.search(pattern, filename):
                return [
                    ('Content-Type', content_type),
                    ('Cache-Control', 'max-age=%d' % cache_life)
                ]
        # else
        return []

    @classmethod
    def cache_life(cls, filename):
        return cls.default_cache_life

    def run_before(self, environ, start_response):
        info = RequestInfo(environ)
        static_path, prefix = self.arguments
        path = info.path

        if prefix and path.startswith(prefix):
            path = path[len(prefix):]
        elif prefix:
            pass

        path = path[1:] if path.startswith('/') else path
        path = path.replace('..', '').replace('//', '')
        localpath = os.path.join(static_path, path)

        if os.path.isfile(localpath):
            # logger.info('Serving file %r', localpath)
            headers = self.get_headers(path)
            headers.append(('X-Local-Path', localpath))
            start_response('200 OK', headers)
            return sendfile(environ, localpath)
        else:
            pass



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
