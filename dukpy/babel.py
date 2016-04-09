import os
from .evaljs import evaljs

BABEL_COMPILER = os.path.join(os.path.dirname(__file__), 'jsmodules', 'babel-6.4.4.min.js')


def babel_compile(source, **kwargs):
    """Compiles the given ``source`` from ES6 to ES5 usin Babeljs"""
    presets = kwargs.get('presets')
    if not presets:
        kwargs['presets'] = ["es2015"]
    with open(BABEL_COMPILER, 'r') as babel_js:
        return evaljs(
            (babel_js.read(),
             'var bres, res;'
             'bres = Babel.transform(dukpy.es6code, dukpy.babel_options);',
             'res = {map: bres.map, code: bres.code};'),
            es6code=source,
            babel_options=kwargs
        )


def jsx_compile(source, mode='react'):
    modes = {
        'react': ["transform-react-jsx"]
    }
    return babel_compile(source, plugins=modes.get(mode, []))['code']
