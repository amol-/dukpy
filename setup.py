#!/usr/bin/env python
import os
from distutils.core import setup, Extension

import sys
py_version = sys.version_info[:2]

HERE = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(HERE, 'README.rst')).read()
except IOError:
    README = ''

INSTALL_REQUIRES = []
if py_version == (2, 6):
    INSTALL_REQUIRES.append('argparse')

duktape = Extension('dukpy._dukpy',
                    define_macros=[('DUK_OPT_DEEP_C_STACK', '1'),
                                   ('DUK_OPT_NONSTD_REGEXP_DOLLAR_ESCAPE', '1'),
                                   ('DUK_OPT_OCTAL_SUPPORT', '1')],
                    sources=[os.path.join('src', 'duktape', 'duktape.c'),
                             os.path.join('src','_support.c'),
                             os.path.join('src','pyduktape.c')],
                    include_dirs=[os.path.join('.', 'src', 'duktape')])

setup(
    name='dukpy',
    version='0.0.4',
    description='Simple JavaScript interpreter for Python',
    long_description=README,
    keywords='javascript compiler babeljs coffeescript typescript',
    author='Alessandro Molina',
    author_email='alessandro.molina@axant.it',
    url='https://github.com/amol-/dukpy',
    license='MIT',
    packages=['dukpy', 'dukpy.webassets'],
    ext_modules=[duktape],
    install_requires=INSTALL_REQUIRES,
    package_data={
        'dukpy': ['jsmodules/*.js', 'jsmodules/react/*.js'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: JavaScript',
    ],
    entry_points={
        'console_scripts': [
            'dukpy-install = dukpy.install:main'
        ]
    }
)
