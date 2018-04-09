import os
from .evaljs import evaljs

BABEL_COMPILER = os.path.join(os.path.dirname(__file__), 'jsmodules', 'babel-6.14.0.min.js')


def babel_compile(source, **kwargs):
    """Compiles the given ``source`` from ES6 to ES5 usin Babeljs"""
    presets = kwargs.get('presets')
    if not presets:
        kwargs['presets'] = ["es2015"]
    with open(BABEL_COMPILER, 'rb') as babel_js:
        return evaljs(
            (babel_js.read().decode('utf-8'),
             'var bres, res;'
             'bres = Babel.transform(dukpy.es6code, dukpy.babel_options);',
             'res = {map: bres.map, code: bres.code};'),
            es6code=source,
            babel_options=kwargs
        )


def jsx_compile(source, **kwargs):
    kwargs['presets'] = ['es2015', 'react']
    return babel_compile(source, **kwargs)['code']
