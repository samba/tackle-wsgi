from flask import Flask, redirect




class Shortener(Flask):

    @classmethod
    def Redirector(cls, destination_url):
        def _method():
            return redirect(destination_url)
        return _method


    def __init__(self, *args, **kwargs):
        self.rules = []
        self.basepath = kwargs.pop('basepath', '/')
        super(Shortener, self).__init__(*args, **kwargs)


    def redirect(self, reference, destination_url):
        handler = self.Redirector(destination_url)
        self.add_url_rule(self.basepath + reference, reference, handler)

