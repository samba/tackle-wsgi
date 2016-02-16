#!/usr/bin/python

from tackle import WSGIApplication, RequestHandler
from tackle import RedirectionMiddleware
from runner import ApplicationTestCase, debug_on

from tackle.decorator import static
# from tackle.middleware import cache


def FixedResponseHandler(text):
    class derived(RequestHandler):
        def get(self):
            return text
    return derived


@debug_on(AttributeError)
def prepareApplication():

    redir = RedirectionMiddleware([
        (r'^/redir_test', 'http://google.com/search?q=redirected')
    ])



    app = WSGIApplication(debug = True)

    app.route(r'/', FixedResponseHandler('main'), allow_prefix = False)
    app.route(r'/redir_test', FixedResponseHandler('redirect failed'))

    @app.route(r'/s/<cache:\d+>/<filename>')
    class StaticHandler(RequestHandler):

        @static('test/static')
        def get(self, cache, filename):
            self.response.cache_expires = int(cache)
            return filename

        def head(self, *a, **kw):
            return self.get(*a, **kw)


    app = redir(app)

    return app


class DecoratorTest(ApplicationTestCase(prepareApplication())):

    def testRedirect(self):
        resp = self.application.get('/redir_test', status=302)
        location = resp.headers.get('Location')
        self.assertResponseBodyNotContains(resp, 'redirect failed')
        self.assertIn('?q=redirected', location)

    @debug_on(AssertionError, TypeError)
    def testStaticRequest(self):
        resp = self.application.get('/s/600/test.txt', status=200)
        cache_ctrl = resp.headers.get('Cache-Control')
        self.assertResponseBodyContains(resp, 'This is a test.')
        self.assertRegexpMatches(cache_ctrl, r'max-age=600')

    def testStaticRequestHEAD(self):
        resp = self.application.head('/s/600/test.txt', status=200)
        self.assertResponseBodyNotContains(resp, 'This is a test.')

    def testRemainingRoute(self):
        resp = self.get('/')
        self.assertResponseBodyContains(resp, 'main')

    def testRemainingRouteTwo(self):
        # This is EXPECTED to yield 404 since we disable prefix match above.
        self.get('/three', status=404)  # implicit test within webob
