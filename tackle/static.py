#!/usr/bin/env python

import os
import re
import hashlib
import datetime
import json
from wsgi import RequestInfo, sendfile
from middleware import Middleware


def md5(*text):
    val = hashlib.md5(text[0])
    for m in text[1:]:
        val.update(m)
    return val.hexdigest()


class StoredResponse(object):
    iso8601 = '%Y-%m-%dT%H:%M:%S.%f'

    def __init__(self, environ, headers = []):
        self.udpated_at = None
        self.headers = headers
        self.status = None
        self.content = None
        self.environ = environ

    def start_response(self, status, headers):
        self.status = status
        self.headers = (headers)
        self.updated_at = datetime.datetime.now()

    def serialize(self, filename, content):
        filename_headers = '%s.headers.txt' % filename
        data = {
            'updated_at': self.updated_at.strftime(self.iso8601),
            'status': self.status,
            'headers': self.headers
        }
        json.dump(data, open(filename_headers, 'wb'))
        with open(filename, 'wb') as output:
            for line in content:
                output.write(line)

        # prepare for retransmission
        self.content = sendfile(self.environ, filename)

    def is_expired(self, ttl=3600):
        now = datetime.datetime.now()
        return (datetime.timedelta(seconds = ttl) + self.updated_at) < now

    @classmethod
    def load(cls, filename, environ):
        filename_headers = '%s.headers.txt' % filename
        data = json.load(open(filename_headers, 'rb'))
        ts = data.get('updated_at', None)
        headers = data.get('headers', [])
        instance = cls(environ, headers = [tuple(i) for i in headers])
        instance.status = data.get('status', None)
        instance.updated_at = datetime.datetime.strptime(ts, cls.iso8601)
        instance.content = sendfile(environ, filename)
        return instance

    def respond(self, start_response, send_body):
        start_response(str(self.status), self.headers)
        return self.content if send_body else []


class StaticCacheMiddleware(Middleware):

    # TODO: pivot to using webob.Response.from_file; integrates
    #   - HTTP status line
    #   - HTTP headers
    #   - HTTP body content

    RE_HEADER_FORMAT = re.compile(r'([A-Za-z0-9_-]+):\s+([^\n]+)')

    def __init__(self, cachepath = ('.static', 'cache'), ttl=3600):

        if isinstance(cachepath, (list, tuple)):
            cachepath = os.path.join(*cachepath)

        self.pool = os.path.join(os.getcwd(), cachepath)
        self.ttl_default = ttl

        super(StaticCacheMiddleware, self).__init__(internal = True)

        try:
            os.makedirs(self.pool)
        except OSError, e:
            pass


    def wsgi_request(self, environ, start_response, app):
        info = RequestInfo(environ)

        if info.method not in ('get', 'head'):
            pass

        ident = md5(info.path_qs)
        source_file = os.path.join(self.pool, ident)

        if os.path.isfile(source_file):
            response = StoredResponse.load(source_file, environ)
        else:
            response = StoredResponse(environ)
            result = app(environ, response.start_response)
            response.serialize(source_file, result)

        return response.respond(start_response, (info.method == 'get'))




