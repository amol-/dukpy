#!/usr/bin/env python
import os
from setuptools import setup, Extension

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

name = 'dukpy'
repo_slug = 'amol-/{0}'.format(name)
repo_url = 'https://github.com/{0}'.format(repo_slug)

setup(
    name=name,
    version='0.2.1',
    description='Simple JavaScript interpreter for Python',
    long_description=README,
    keywords='javascript compiler babeljs jsx coffeescript typescript',
    author='Alessandro Molina',
    author_email='alessandro.molina@axant.it',
    url=repo_url,
    project_urls={
        'CI: AppVeyor': 'https://ci.appveyor.com/project/{0}'.format(repo_slug),
        'CI: Travis': 'https://travis-ci.org/{0}'.format(repo_slug),
        'GitHub: issues': '{0}/issues'.format(repo_url),
        'GitHub: repo': repo_url,
    },
    license='MIT',
    packages=['dukpy', 'dukpy.webassets'],
    ext_modules=[duktape],
    install_requires=INSTALL_REQUIRES,
    extras_require={
        'testing': [
            'coveralls',
            'nose',
            'mock',
        ],
        'webassets': [
            'webassets',
        ],
    },
    package_data={
        'dukpy': ['jscore/*.js', 'jsmodules/*.js', 'jsmodules/react/*.js',
                  'jsmodules/less/*/*.js', 'jsmodules/less/*/*/*.js'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: JavaScript',
    ],
    entry_points={
        'console_scripts': [
            'dukpy-install = dukpy.install:main',
            'dukpy = dukpy.run:main'
        ]
    }
)
