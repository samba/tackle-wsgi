from tackle import WSGIApplication, RequestHandler
from tackle import RedirectionMiddleware
from runner import ApplicationTestCase, debug_on

from tackle.blog import BlogRequestHandler, BlogIndex

app = WSGIApplication()


class Blog(BlogRequestHandler):
    CONTENT_PATH = 'test/blog_content'
    pass


Blog.attach_route(app)

class BlogTest(ApplicationTestCase(app)):
    INDEX_TTL = -1

    @debug_on(TypeError, ValueError)
    def testWriteIndex(self):
        index = BlogIndex('test/blog_content', '.blog_index.json')
        index.generate_index('.blog_index.json')

    def testBlogEntryRequest(self):
        resp = self.application.get('/blog/1982/awesome/first-blog-post')
        self.assertResponseBodyContains(resp, "super awesome")
