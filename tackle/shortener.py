from tackle.wsgi import RedirectionMiddleware




class Shortener(RedirectionMiddleware):
    """ A simple abstraction for redirection.

        Usage:
            shortener = Shortener(basepath = "/s/")

            # /s/abc => 302 http://abc.com
            shortener.redirect('abc', 'http://abc.com')

    """


    def __init__(self, *args, **kwargs):
        self.basepath = kwargs.pop('basepath', '/')
        super(Shortener, self).__init__(*args, **kwargs)

    def redirect(self, reference, destination_url, permanent = False):
        pattern = self.basepath + reference + '$'
        super(Shortener, self).redirect(pattern, destination_url, permanent)
