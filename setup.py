#from distutils.core import setup
from setuptools import setup
from pyxdebug import __version__, __author__, __license__
 
setup(
    name             = 'pyxdebug',
    version          = __version__,
    description      = 'PyXdebug is Xdebug format debugger for Python',
    long_description = open('README').read(),
    author           = __author__,
    author_email     = 'tetu@eth0.jp',
    url              = 'http://github.com/eth0jp/python-xdebug',
    keywords         = 'xdebug profile profiler',
    license          = __license__,
    py_modules       = ['pyxdebug'],
    classifiers      = ["Development Status :: 5 - Production/Stable",
                        "Intended Audience :: Developers",
                        "License :: OSI Approved :: MIT License",
                        "Operating System :: POSIX",
                        "Operating System :: MacOS",
                        "Programming Language :: Python",
                        "Programming Language :: PHP",
                        "Topic :: Software Development :: Debuggers",
                        "Topic :: Software Development :: Libraries :: Python Modules"]
)
