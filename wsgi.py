
from webob import exc as exceptions
from webob import Request, Response

from util import cached_property

import re
import os


import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())



class RequestInfo(object):

    @classmethod
    def gethostname(cls, environ):
        return environ.get('HTTP_HOST', None).split(':')[0]

    def __init__(self, environ):
        self.environ = environ

    @property
    def hostname(self):
        return self.gethostname(self.environ)

    @property
    def path(self):
        script = self.environ.get('SCRIPT_NAME', '')
        path = self.environ.get('PATH_INFO', '')
        return script + path



class FileWrapper(object):

    def __init__(self, filelike, blksize=8192):
        if not callable(getattr(filelike, 'read', None)):
            raise TypeError("response.FileWrapper requires a file-like object")

        self.filelike = filelike
        self.blksize = blksize
        if hasattr(filelike, 'close'):
            self.close = filelike.close

    def __getitem__(self, key):
        data = self.filelike.read(self.blksize)
        if data:
            return data
        raise IndexError



def sendfile(environ, filepath):
    handler = environ.get('wsgi.file_wrapper', FileWrapper)
    return handler(open(filepath, 'rb'))




class WSGIRequestHandler(object):

    pass_all_match_groups = False
    environ = None

    def __init__(self, request, response, match):
        self.request = request
        self.response = response
        self.arguments = self.match_arguments(match)

    def sendfile(self, filename):
        return sendfile(self.environ, filename)

    @classmethod
    def match_arguments(cls, match):
        kwargs = match.groupdict()
        kwargs_index = match.re.groupindex.values()
        args = []

        if cls.pass_all_match_groups:
            for index in range(1, match.lastindex):
                if index not in kwargs_index:
                    args.append(index)
            return match.group(*args), kwargs
        else:
            """ This is compatible with Django's routing;
                If the route pattern generated keyword matches, then call
                the handler with only keyword arguments. Otherwise, call
                the handler with only positional arguments. """
            if len(kwargs_index):
                return args, kwargs
            else:
                return match.groups(), kwargs

    def __call__(self, environ, start_response):
        method = getattr(self, self.request.method.lower(), None)
        self.environ = environ

        if not callable(method):
            raise exceptions.HTTPNotImplemented

        else:
            args, kwargs = self.arguments
            # logger.info('Request arguments, %r, %r' % (args, kwargs))
            result = method.__call__(*args, **kwargs)

            if isinstance(result, basestring):
                self.response.write(result)

            return self.response(environ, start_response)





class WSGIRoute(object):
    RE_PARSE_PATH = re.compile(r'<([a-zA-Z_]+)?(?::([^>]+))?>')

    def __init__(self, path, handler, name = None):
        self.name = name
        self.path = path
        self.handler = handler

    @cached_property
    def template(self):
        return self.RE_PARSE_PATH.sub(r"\1", self.path)

    @cached_property
    def matchpattern(self):
        def _sub(match):
            name, pattern = match.group(1, 2)
            if name:
                return '(?P<%s>%s)' % (name, (pattern or '[^/]+'))
            else:
                return '(%s)' % pattern
        return re.compile(self.RE_PARSE_PATH.sub(_sub, self.path))

    def match(self, path):
        m = self.matchpattern.match(path)
        if m is None:
            return None, None
        else:
            return m, self.handler


class WSGIRouter(object):

    def __init__(self, application):
        self.application = application
        self.routes = []
        self.named_routes = {}

    def register(self, route):
        self.routes.append(route)
        route_name = getattr(route, 'name', None)
        if route_name:
            self.named_routes[route_name] = route

    def dispatch(self, environ, request):
        for r in self.routes:
            match, handler = r.match(request.path)
            if match:
                return match, handler

        # else
        raise exceptions.HTTPNotFound




class WSGIApplication(object):

    requesthandler_class = WSGIRequestHandler
    router_class = WSGIRouter
    route_class = WSGIRoute

    def __init__(self, *routes, **options):
        self.router = self.router_class(self)
        for route in routes:
            if isinstance(route, self.route_class):
                self.router.register(route)
            elif isinstance(route, tuple):
                self.router.register(self.route_class(*route))

    def route(self, path, **opts):
        def _decorator(handler):
            route = self.route_class(path, handler, **opts)
            self.router.register(route)
            return route
        return _decorator


    def __call__(self, environ, start_response):
        request = Request(environ)
        try:
            match, handler = self.router.dispatch(environ, request)
            if issubclass(handler, self.requesthandler_class):
                handler = (handler(request, Response(), match))
                return handler(environ, start_response)

            elif callable(handler):
                response = Response(handler(request, match))

        except exceptions.HTTPException, e:
            response = e

        return response(environ, start_response)



class WSGIService(object):
    """A simple virtual host router based on hostname."""

    application_class = WSGIApplication

    def __init__(self, *routes):
        self.hostmap = {}
        for host, app in routes:
            self.register(app, host)

    def register(self, app, *hostnames):
        assert callable(app) or isinstance(app, self.application_class)
        for hostname in hostnames:
            self.hostmap[hostname] = app


    def __call__(self, environ, start_response):
        request_host = RequestInfo.gethostname(environ)

        if request_host in self.hostmap:
            return (self.hostmap[request_host])(environ, start_response)
        else:
            start_response(
                "503 Service Unavailable",
                [ ('Content-Type', 'text/plain') ])
            return [
                "The requested site (%s) is not currently configured." % (
                    request_host
                ) ]


class VirtualHostRouter(WSGIService):
    """ A compatibility class """
    pass


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
