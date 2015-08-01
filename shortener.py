from flask import Flask, redirect




class Shortener(object):

    @classmethod
    def Redirector(cls, destination_url):
        def _method():
            return redirect(destination_url)
        return _method


    def __init__(self, *args, **kwargs):
        self.rules = []
        self.basepath = kwargs.pop('basepath', '/')
        if isinstance(args[0], Flask):
            self.app = args[0]
        else:
            self.app = Flask(__name__, *args, **kwargs)


    def redirect(self, reference, destination_url):
        handler = self.Redirector(destination_url)
        self.app.add_url_rule(self.basepath + reference, reference, handler)

    def __call__(self, environ, start_response):
        return self.app.__call__(environ, start_response)

