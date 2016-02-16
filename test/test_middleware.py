#!/usr/bin/python

from tackle import WSGIApplication, RequestHandler
from tackle import RedirectionMiddleware, StaticFileMiddleware
from runner import ApplicationTestCase, debug_on


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


    static = StaticFileMiddleware(
        local_path = 'test/static',
        static_prefix = '/static'
    )

    app = WSGIApplication(debug = True)
    app.route(r'/', FixedResponseHandler('main'), allow_prefix = False)
    app.route(r'/redir_test', FixedResponseHandler('redirect failed'))

    app = static(app)
    app = redir(app)

    return app


class DecoratorTest(ApplicationTestCase(prepareApplication())):

    def testRedirect(self):
        resp = self.get('/redir_test', status=302)
        location = resp.headers.get('Location')
        self.assertResponseBodyNotContains(resp, 'redirect failed')
        self.assertIn('?q=redirected', location)


    def testStaticRequest(self):
        resp = self.get('/static/test.txt', status=200)
        self.assertResponseBodyContains(resp, 'This is a test.')

    def testRemainingRoute(self):
        resp = self.get('/')
        self.assertResponseBodyContains(resp, 'main')


    def testRemainingRouteTwo(self):
        # This is EXPECTED to yield 404 since we disable prefix match above.
        self.get('/three', status=404)  # implicit test within webob
