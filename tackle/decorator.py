#!/usr/bin/env python

"""Decorator methods to integrate features on request handlers"""

from webob.static import FileApp
from webob import Response
from wsgi import WSGIRequestHandler
from proxy import ResponseInterceptor
import os


def is_member_handler(args):
    return len(args) and isinstance(args[0], WSGIRequestHandler)


def get_response(args):
    return (args[0].response
            if is_member_handler(args)
            else Response(conditional_response=True))


def static(local_path, method=None):
    """Decorator for methods returning static files.
        The method must return the desired filename within the given path.
    """

    def _apply(handler):
        def action(*args, **kwargs):
            filename = handler(*args, **kwargs)
            filename = os.path.join((local_path or os.getcwd()), filename)
            response = get_response(args)
            return ResponseInterceptor(FileApp(filename), response).wsgi

        action.__name__ = handler.__name__
        action.__doc__ = handler.__doc__
        return action

    return _apply

