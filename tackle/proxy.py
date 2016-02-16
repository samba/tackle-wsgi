
from webob import Response
from wsgi import logger


class ResponseInterceptor(object):
    def __init__(self, app, response, **kwargs):
        self.app = app
        self.response = response or Response(**kwargs)

    def intercept(self, response):
        pass

    def _start(self, status, headers):
        self.response.status = status
        for k, v in headers:
            self.response.headers[k] = v
        # logger.info('Headers integrated, %r' % (self.response.headers))

    def wsgi(self, environ, start_response):
        # logger.info('Starting response from %r', self.app)
        result = self.app(environ, self._start)
        # logger.info('Result of %r: %r' % (self.app, result))
        if isinstance(result, basestring):
            self.response.text = unicode(result)
        elif callable(result):
            result = (self.__class__(result, self.response))
            return result(environ, start_response)
        else:
            self.response.app_iter = result

        if callable(self.intercept):
            r = self.intercept(self.response)
            if isinstance(r, Response):
                self.response = r

        return self.response(environ, start_response)

    def __call__(self, environ, start_response):
        return self.wsgi(environ, start_response)
