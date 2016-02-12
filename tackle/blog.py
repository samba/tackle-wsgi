#!/usr/bin/env python
"""Simple blog management kit using Markdown."""

from tackle import RequestHandler, WSGIApplication

import json
import mistune
import datetime
import logging
import os
import re

from mistune_contrib import (
    highlight, math, toc
)


from mistune_contrib.meta import parse as parse_meta


def getLogger(cls, add_stream_handler=True):
    if (type(cls) not in ('class',)):
        cls = type(cls)

    logger = logging.getLogger('%s.%s' % (cls.__module__, cls.__name__))

    if add_stream_handler:
        logger.addHandler(logging.StreamHandler())

    return logger

DATETIME_FORMATS = (
    '%Y-%m-%dT%H:%M:%S.%f',
    '%Y-%m-%d %H:%M:%S %Z',
    '%d %b %Y %H:%M:%S %Z',
    '%B %d, %Y %H:%M:%S %Z',
    '%d. %B %Y %H:%M:%S %Z',
    '%d %b %Y',
    '%d. %B %Y',
    '%B %d, %Y',
    '%Y-%m-%d'
)


class MistuneMetaMixin(mistune.Renderer):
    """Simple extension to load metadata."""

    meta = None

    def parse(self, text):
        """First extract metadata, then run standard parser."""
        meta, text = parse_meta(text)
        self.meta = meta
        return super(MistuneMetaMixin, self).parse(text)


class Renderer(highlight.HighlightMixin,
               math.MathRendererMixin,
               MistuneMetaMixin):
    """Integration class for desired features."""

    pass


class MarkdownBlog(mistune.Markdown):
    """Converts a Markdown file to page content (HTML)."""

    def __init__(self):
        """Prepare a Markdown rendere with syntax highlighting support."""
        super(MarkdownBlog, self).__init__(
            renderer=Renderer(escape=False, use_xhtml=True, hard_wrap=True)
        )

    @property
    def metadata(self):
        """Accessor to metadata if available."""
        return getattr(self.renderer, 'meta', None)


class BlogPostEntry(MarkdownBlog):

    RE_TAGSPLIT = re.compile(r',\s*')
    RE_BAD_URLCHARS = re.compile(r'[^a-z0-9-]+')

    def __init__(self, filename, metadata, text, config):
        super(BlogPostEntry, self).__init__()
        self.filename = filename
        self.meta = metadata
        self.text = text
        self.config = config

    def parse_date(self, date_expr):
        for fmt in DATETIME_FORMATS:
            try:
                result = datetime.datetime.strptime(date_expr, fmt)
                return result
            except ValueError:
                continue

    @property
    def title(self):
        return self.meta.get('Title',
                             self.config.get('Default-Title', 'Untitled'))

    @property
    def title_stub(self):
        stub = self.RE_BAD_URLCHARS.sub('-', self.title.lower())
        if not stub:
            stub, ext = os.path.splitext(os.path.filename(self.filename))
        return stub

    @property
    def category(self):
        tags = self.tags
        alt_category = (tags[0] if len(tags) else 'blog') or 'blog'
        return self.meta.get('Category', alt_category)

    @property
    def author(self):
        return self.meta.get('Author', self.config.get('Author'))

    @property
    def tags(self):
        return self.RE_TAGSPLIT.split(self.meta.get('Tags', ''))

    @property
    def tagstring(self):
        return ', '.join(self.tags)

    def summary(self, textlen=None):
        """Retrieve a summary text for the post, from its content if needed."""
        textlen = textlen or self.config.get('Summary-Text-Limit', 200)
        summary = self.meta.get('Summary', None)
        if summary is None:
            summary = self.text[0:(textlen + 30)].strip()
        return summary[0:textlen]

    @property
    def published_date(self):
        return self.parse_date(self.meta.get('Date', None))

    @property
    def updated_date(self):
        return self.parse_date(self.meta.get('Updated', self.published_date))

    @property
    def content(self):
        return self.render(self.text)

    @property
    def year(self):
        published = self.published_date
        return published.timetuple().tm_year if published else '0000'

    def generate_slug(self, fmt):
        return re.sub(r'/+', '/', fmt.format(
            year=self.year,
            title=self.title_stub,
            category=self.category
        ))


class BlogRequestHandler(RequestHandler):

    REQUEST_FORMAT = '{year}/{category}/{title}'
    CONTENT_PATH = 'blog'
    INDEX_FILE = '.blog_index.json'
    INDEX_TTL = 3600

    @classmethod
    def attach_route(cls, app, prefix='/blog/'):
        if isinstance(app, WSGIApplication):
            _route = cls.REQUEST_FORMAT.replace('{', '<').replace('}', '>')
            return app.route(prefix + _route)(cls)

    def get(self, **kwargs):
        lookup = self.REQUEST_FORMAT.format(**kwargs)
        index = BlogIndex(self.CONTENT_PATH, self.INDEX_FILE)
        try:
            entry = index.getEntryLookup(lookup, ttl=self.INDEX_TTL)
            return entry.content
        except KeyError:
            self.response.set_status(404, 'Not Found')






class BlogIndex(object):
    """Scan and parse important data from a directory of markdown files."""

    REQUEST_FORMAT = BlogRequestHandler.REQUEST_FORMAT
    RE_MARKDOWN_EXTENSION = re.compile(r'\.(markdown|md(o?wn)?|mkdn?|text)$')

    def __init__(self, path, index_file, **kwargs):
        self.path = path
        self.config = kwargs
        self.index_file = index_file

    def getEntry(self, filename):
        meta, text = parse_meta(open(filename, 'rb').read())
        return BlogPostEntry(filename, meta, text, self.config)

    def scan(self, path=None):
        logger = getLogger(self)
        logger.setLevel(logging.INFO)
        # logger.info('Scanning directory: %s' % (path or self.path))
        for fname in os.listdir(path or self.path):
            is_markdown = self.RE_MARKDOWN_EXTENSION.search(fname)
            fname = os.path.join((path or self.path), fname)
            if os.path.isfile(fname) and is_markdown:
                # logger.info('Loading file: %s' % (fname))
                yield self.getEntry(fname)

    def getEntryLookup(self, lookup, ttl=3600):
        index = self.fetch_index(self.index_file, ttl=ttl)
        fname = index.get('entries', {}).get(lookup)
        if fname is not None:
            return self.getEntry(fname)
        else:
            raise KeyError("Could not resolve lookup: %s" % lookup)

    @property
    def index(self):
        return self.fetch_index(self.index_file)

    def fetch_index(self, index_file, ttl=3600):
        needs_update = False
        if os.path.isfile(index_file):

            try:
                content = json.load(open(index_file, 'rb'))
                iso8601 = DATETIME_FORMATS[0]
                updated = content.get('updated_at', None)
                updated = datetime.datetime.strptime(updated, iso8601)
                delta = datetime.timedelta(seconds=ttl)

                if (updated + delta) > datetime.datetime.now():
                    needs_update = True
            except:
                needs_update = True
        else:
            needs_update = True

        if needs_update:
            content = self.generate_index(index_file)

        return content

    def generate_index(self, index_file):
        iso8601 = DATETIME_FORMATS[0]
        content = { 'updated_at': datetime.datetime.now().strftime(iso8601) }
        records = {}
        for entry in self.scan():
            url = entry.generate_slug(self.REQUEST_FORMAT)
            records[url] = entry.filename
        content['entries'] = records
        json.dump(content, open(index_file, 'wb'))
        return content


