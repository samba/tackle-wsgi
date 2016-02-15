#!/usr/bin/python

from tackle import BuildApplication, RequestHandler
from tackle import RedirectionMiddleware, StaticFileMiddleware
from runner import ApplicationTestCase, debug_on


def FixedResponseHandler(text):
    class derived(RequestHandler):
        def get(self):
            return text
    return derived


@debug_on(AttributeError)
def prepareApplication():

    app = BuildApplication(RedirectionMiddleware, StaticFileMiddleware)
    app.route(r'/', FixedResponseHandler('main'))
    app.route(r'/redir_test', FixedResponseHandler('redirect failed'))

    app.redirect(r'^/redir_test', 'http://google.com/search?q=redirected')
    app.static_path = 'test/static'
    app.static_prefix = '/static'
    return app


class DecoratorTest(ApplicationTestCase(prepareApplication())):

    def testRedirect(self):
        resp = self.application.get('/redir_test', status=302)
        location = resp.headers.get('Location')
        self.assertIn('?q=redirected', location)

    def testStaticRequest(self):
        resp = self.application.get('/static/test.txt', status=200)
        self.assertResponseBodyContains(resp, 'This is a test.')

    def testRemainingRoute(self):
        resp = self.application.get('/')
        self.assertResponseBodyContains(resp, 'main')
