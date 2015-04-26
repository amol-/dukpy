import os
from .evaljs import evaljs

BABEL_COMPILER = os.path.join(os.path.dirname(__file__), 'babel-4.6.6.min.js')


def babel_compile(source):
    """Compiles the given ``source`` from ES6 to ES5 usin Babeljs"""
    with open(BABEL_COMPILER, 'r') as babel_js:
        return evaljs(
            (babel_js.read(),
             'babel.transform(dukpy.es6code).code'),
            es6code=source
        )
