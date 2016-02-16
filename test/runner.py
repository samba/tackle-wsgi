
# A convenient test runner integrating unittest & coverage modules.

import os
import sys
import webtest
import unittest
import contextlib
import coverage as lib_coverage
import logging
import pdb
import functools
import traceback


from webtest import AppError

def dirname_up(path, howmany = 1):
    while (howmany > 0):
        path = os.path.dirname(path)
        howmany = howmany - 1
    return path


def debug_on(*exceptions):
    if not exceptions:
        exceptions = (AssertionError, )

    def decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except exceptions:
                info = sys.exc_info()
                traceback.print_exception(*info)
                pdb.post_mortem(info[2])
        return wrapper
    return decorator


class TestApp(webtest.TestApp):
    logger = logging.getLogger(__name__)

    @classmethod
    def logging_enable(cls):
        cls.logger.setLevel(logging.DEBUG)
        cls.logger.addHandler(logging.StreamHandler())


    @contextlib.contextmanager
    def service(self, app):
        try:
            service = webtest.StopableWSGIServer.create(app)
            yield service, service.adj.host, service.adj.port
        finally:
            service.shutdown()


# To be called as a dynamic parent class for test cases.
def ApplicationTestCase(app):
    class TestCase(unittest.TestCase):
        application = TestApp(app)

        @debug_on(AppError, AttributeError, IndexError, KeyError, ValueError)
        def get(self,  *args, **opts):
            return self.application.get(*args, **opts)


        def assertResponseStatus(self, response, *status):
            self.assertIn(response.status_int, status)

        def assertResponseContentType(self, response, content_type):
            self.assertEqual(response.content_type, content_type)

        def assertResponseBodyIs(self, response, content):
            self.assertEqual(response.normal_body, content)

        def assertResponseBodyContains(self, response, content):
            self.assertIn(content, response.normal_body)

        def assertResponseBodyNotContains(self, response, content):
            self.assertNotIn(content, response.normal_body)

    return TestCase




@contextlib.contextmanager
def coverage():
    try:
        cov = lib_coverage.Coverage(timid = False, branch = True)
        # cov.exclude()
        cov.start()
        yield
    finally:
        cov.stop()
        cov.save()
        cov.report(omit = (r'*/lib/python*', r'*/runner.py'))


def runtests(paths, top = None, verbosity = 2):
    if top is None:
        top = dirname_up(__file__, 2)
    loader = unittest.loader.TestLoader()
    suiteAll = unittest.TestSuite()
    for p in paths:
        suite = loader.discover(p, pattern = 'test_*.py', top_level_dir = top)
        suiteAll.addTests(list(suite))

    unittest.TextTestRunner(verbosity = verbosity).run(suiteAll)


def main(args):
    TestApp.logging_enable()
    with coverage():
        runtests(args)

if __name__ == '__main__':
    main(sys.argv[1:])
