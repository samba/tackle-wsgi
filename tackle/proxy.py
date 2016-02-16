
from webob import Response
from wsgi import logger


class ResponseInterceptor(object):
    def __init__(self, app, response, **kwargs):
        self.app = app
        self.response = response or Response(**kwargs)

    def intecept(self, response):
        pass

    def _start(self, status, headers):
        self.response.status = status
        for k, v in headers:
            self.response.headers[k] = v
        logger.info('Headers integrated, %r' % (self.response.headers))

    def wsgi(self, environ, start_response):
        logger.info('Starting response from %r', self.app)
        result = self.app(environ, self._start)
        logger.info('Result of %r: %r' % (self.app, result))
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




class ProxyResponse(object):
    """Provides a staging area for response inspection and modification."""

    def __init__(self, upstream, headers = None):
        self.status = '200 OK'
        self.headers = ([] if headers is None else list(headers))
        self.content = None
        self.upstream = upstream

    def start_response(self, status, headers):
        self.status = status
        self.headers = headers

    def intercept(self):
        pass

    def clear(self):
        self.content = None
        del self.headers[:]

    def wsgi(self, environ, start_response = None):
        """Relay a request, intercept the response."""
        self.content = self.upstream(environ, self.start_response)
        try:
            self.intercept()
            if callable(start_response):
                start_response(self.status, self.headers)
            return self.content
        except:
            return self.content


    def __call__(self, environ, start_response):
        """Produce response as a WSGI responder."""
        return self.wsgi(environ, start_response)

