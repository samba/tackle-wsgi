#!/usr/bin/python

from tackle import WSGIApplication, RequestHandler
from tackle import RedirectionMiddleware
from runner import ApplicationTestCase

app = WSGIApplication()

@app.route('/')
class MainRequestHandler(RequestHandler):
    def get(self):
        return 'Hi there!'

    def post(self):
        whatever = self.request.params.get('whatever', None)
        if whatever is None:
            self.response.set_status(404, 'Not Found')
        else:
            self.response.set_status(201, 'Created')

        return whatever or 'NOT GIVEN'

redir = RedirectionMiddleware()
redir.redirect(r'^/wompwompwomp', 'http://google.com/search?q=womp')

app = redir.wsgi(app)

class TestCaseAlpha(ApplicationTestCase(app)):
    def testRootQuery(self):
        resp = self.application.get('/')
        self.assertResponseStatus(resp, 200)
        self.assertResponseBodyIs(resp, "Hi there!")

    def testPostQuery(self):
        resp = self.application.post('/', {'whatever': '2'}, status = 201)
        self.assertResponseBodyIs(resp, '2')

    def testPostQueryInvalid(self):
        resp = self.application.post('/', {'another': '2'}, status=404)
        self.assertResponseBodyIs(resp, 'NOT GIVEN')

    def testRedirect(self):
        resp = self.application.get('/wompwompwomp', status=302)
        self.assertResponseStatus(resp, 302)
        self.assertIn('?q=womp', resp.headers.get('Location'))
