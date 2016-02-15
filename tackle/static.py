#!/usr/bin/env python

import os
import hashlib
from wsgi import RequestInfo

def md5(*text):
    val = hashlib.md5(text[0])
    for m in text[1:]:
        val.update(m)
    return val.hexdigest()

class StaticCache(object):

    def __init__(self, cachepath = ('.static', 'cache'), ttl=3600):

        if isinstance(cachepath, (list, tuple)):
            cachepath = os.path.join(*cachepath)

        cachepath = os.path.join(os.getcwd(), cachepath)


    def attach(self, handler):
        """Decorator for WSGI-compatible methods"""


        def q(environ, start_response):
            info = RequestInfo(environ)
            ident = md5(info.path_qs)

            if ident not in self.cachepool:
                # TODO: generate content through bandler
                # TODO: store cached copy

            # TODO: respond with cache & headers


