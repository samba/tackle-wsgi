from webservice.wsgi import RedirectionMiddleware




class Shortener(RedirectionMiddleware):

    def __init__(self, *args, **kwargs):
        self.basepath = kwargs.pop('basepath', '/')
        super(Shortener, self).__init__(*args, **kwargs)

    def redirect(self, reference, destination_url):
        pattern = self.basepath + reference + '$'
        super(Shortener, self).redirect(pattern, destination_url, False)
