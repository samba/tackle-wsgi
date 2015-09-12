from webservice import __version__, __author__, __license__
from setuptools import setup

setup(
    name = 'tackle',
    description = 'Another WSGI framework aiming for simplicity and flexibility',
    version = __version__,
    author = __author__,
    license = __license__,

    packages = [ 'tackle' ],

    install_requires = ['WebOb'],
    install_package_data = True,
    scripts = [],
    zip_safe = True
)
