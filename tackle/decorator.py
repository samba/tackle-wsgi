from webob.static import FileApp
from webob import Response
from wsgi import  WSGIRequestHandler
from proxy import ResponseInterceptor
import os


class CacheInterceptor(ResponseInterceptor):

    def intercept(self, response):
        # logger.info('Marking response %r' % response)
        self.response.headers.add('X-test', 'true')


def static(local_path, method = None):
    """Decorator for methods returning static files.
        The method must return the desired filename within the given path.
    """

    def _cache(response):
        response.headers.add('X-Test', 'true')

    def _apply(handler):
        def action(*args, **kwargs):
            filename = handler(*args, **kwargs)
            filename = os.path.join((local_path or os.getcwd()), filename)

            if (len(args) and isinstance(args[0], WSGIRequestHandler)):
                response = args[0].response
            else:
                response = Response(conditional_response=True)
            return CacheInterceptor(FileApp(filename), response).wsgi
            return FileApp(filename)

        action.__name__ = handler.__name__
        action.__doc__ = handler.__doc__
        return action

    return _apply


def cache(lifetime):
    def _apply(handler):
        def action(self, *args, **kwargs):
            result = handler(*args, **kwargs)
            if isinstance(result, Response):
                result.cache_expires = lifetime
            else:
                self.response.cache_expires = lifetime
            return result
        return action
    return _apply
