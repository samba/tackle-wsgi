# WSGI Tackle 

This is a WSGI framework originated by Sam Briesemeister, derived from work in personal projects and products still in development, which needed a very light WSGI abstraction.

It adopts some inspiration, paradigms and design components from other WSGI environments, including webapp2 (Google AppEngine), but aims to maintain a degree of compatibility with core WSGI architecture.

It's currently tested and working in combination with Flask. No dependencies on a particular WSGI server, e.g. `gevent`, are currently required. 

## Why does the world need another WSGI framework?

Frankly *the world* probably doesn't, but in spite of the [abundance of available frameworks](http://wsgi.readthedocs.org/en/latest/frameworks.html), none quite fit my taste. 

The name: tackle, [the equipment used to in a particular sport](http://www.thefreedictionary.com/tackle). 

## Dependencies

- webob

## Development Status

Note the version number. Still _very_ early in development.

# Features

- [Virtual Host Routing](#virtualhost) based on hostname
- [URL Routing](#routing) with regular expressions to simplify RESTful interface design (which most modern WSGI frameworks also claim)
- [Middleware Class](#middleware) for easily mixing features, in generic fashion, with existing WSGI applications.
  - [Static File Preemptive Route](#staticfiles-middleware)
  - [Rule-based Redirection](#redirection-middleware)


## Virtual Host Routing <a id='virtualhost'></a>

In case you're using a very simplistic hosting environment which offers you a single WSGI instance, such as Gandi's Simple Hosting, you may need to integrate multiple WSGI applications from several domains.

```python
from tackle import WSGIService
from myapp import example_com
from myapp import otherhost_com

# Pass any WSGI-compliant callable as a hander for any host.

service = WSGIService(
  ('www.example.com', example_com)
  ('www.otherhost.com', otherhost_com)
)

# Register a single WSGI callable for multiple hosts
service.register(another_app, 'abc.com', 'xyz.com')

```


## URL Routing <a id='routing'></a>

This model probably isn't new to you, it's echoed in many frameworks, in various styles.
Register a RequestHandler for a particular URL pattern.

```python
from tackle import WSGIApplication, WSGIRequestHandler

app = WSGIApplication()

@app.route('/resource/<resource_id>')
class ResourceHandler(WSGIHandler):

  def get(self, resource_id):
    """ retrieve the resource's content """
    # self.response is a webob.Response
    self.response.headers['Content-Type'] = 'text/plain'
    return "Looking for resource %r" % resource_id

  def post(self, resource_id):
    """ update the resource based on request body """
    # self.request is a webob.Request
    update_prop = self.request.params.get('resource_name')
    pass

```

Currently there are no artificial constraints on HTTP verbs that will be attempted as methods on the request handler. 



## Middleware <a id="middleware"></a>

A simple, generic Middleware model is provided. Any middleware derived from this class can implement one or both of the methods illustrated below, `run_before` or `run_after`.

```python
from tackle import Middleware, WSGIApplication

class CustomMiddleware(Middleware):

  def run_before(self, environ, start_response):
    # any aspects accessible to downstream applications need to be added to environ.
    # a return value from this method will override (prevent) the downstream app from handling the request.
    pass

  def run_after(self, environ, start_response, previous_result):
    # `previous_result` is the return value from the app, or any intervening Middleware.
    # this method should return previous_result, if unmodified, or return a modified form of it (a replacement).
    return previous_result

  
# Prepare your core WSGI application.
myapp = WSGIApplication(...)

# Constructs a new WSGI callable. 
# If you reassign `app` with this value, you may lose reference to your original app's properties. 
wrapped_app = CustomMiddleware(option = "value").wsgi(myapp)


```


### Static File Preemptive Route <a id="staticfiles-middleware"></a>

This middleware acts as a preemptor to a primary application. When a request matches the given URL prefix, the remaining URL path is resolved within a given local directory, and served directly with a simple caching directive.

```python
from tackle import WSGIApplication, StaticFileMiddleware

# All requests in "/static/" should resolve within "./local/app/static"
# e.g. GET /static/site.css will resolve to "local/app/static/site.css"
static = StaticFileMiddleware('local/app/static', '/static/')

app = WSGIApplication()
app = static.wsgi(app)

```

### Rule-Based Redirection <a id="redirection-middleware"></a>

The Redirection middleware operates preemptively, intercepting requests to matched URLs and responding with HTTP 301 or 302 redirects.

Two options are provided to incorporate common behaviors; `retain_path` will first copy the path from the original request into the redirect's destination; and `retain_query` will first copy the query from the original request into the redirect's destination. 
These options will override statically-defined path or query components of the configured target. Variations can be achieved using regular expressions and destination templates.

```python
from tackle import WSGIApplication, RedirectionMiddleware

app = WSGIApplication()

redir = RedirectionMiddleware(retain_path = False, retain_query = True) # defaults
redir.redirect("/help/(.*)", "http://help.mysite.com/{1}")

# named captures are also supported.
redir.redirect("/help/(?P<article>.*)", "http://help.mysite.com/{article}")

app = redir.wsgi(app)

```

