import os as _os

from .evaljs import evaljs as _evaljs

__all__ = ("jsx_compile",)


def jsx_compile(source, **kwargs):
    kwargs["presets"] = ["es2015", "react"]
    with open(_BABEL_COMPILER, "rb") as babel_js:
        return _evaljs(
            (
                babel_js.read().decode("utf-8"),
                "var bres, res;"
                "bres = Babel.transform(dukpy.es6code, dukpy.babel_options);",
                "res = {map: bres.map, code: bres.code};",
            ),
            es6code=source,
            babel_options=kwargs,
        )["code"]


_BABEL_COMPILER = _os.path.join(
    _os.path.dirname(__file__), "jsmodules", "babel-6.26.0.min.js"
)
