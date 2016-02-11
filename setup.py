from tackle import __version__, __author__, __license__
from setuptools import setup

from pip.req import parse_requirements
from pip.download import PipSession

import re

def parse_authors(author_list):
    for author in author_list:
        props = re.match(r'^([^\n<>]+)\s<([^>]+)>$', author)
        if props:
            yield props.group(1, 2)  # (name, email)
        
def compose_authors(author_list):
    names, emails = [], []
    for name, email in parse_authors(author_list):
        names.append(name)
        emails.append(email)
    return ', '.join(names), ', '.join(emails)

requirements = parse_requirements("requirements.txt", session=PipSession()) 

author_names, author_emails = compose_authors(__author__)

setup(
    name = 'tackle',
    description = 'Another WSGI framework aiming for simplicity and flexibility',
    version = __version__,
    license = __license__,

    author = author_names,
    author_email = author_emails,

    maintainer = author_names,
    maintainer_email = author_emails,

    contact = author_names,
    contact_email = author_emails,

    packages = [ 'tackle' ],

    install_requires = [str(r.req) for r in requirements],
    include_package_data = True,
    scripts = [],
    zip_safe = True,

    url = "https://github.com/samba/tackle-wsgi/"
)
