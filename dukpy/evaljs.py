import json
from . import _dukpy

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

try:
    unicode
    string_types = (str, unicode)
except NameError:  #pragma: no cover
    string_types = (bytes, str)


class JSInterpreter(object):
    def __init__(self):
        self._ctx = _dukpy.create_context()

    def eval(self, code, **kwargs):
        jsvars = json.dumps(kwargs)
        jscode = code

        if not isinstance(code, string_types):
            jscode = ';\n'.join(code)

        res = _dukpy.eval_string(self._ctx, jscode, jsvars)
        if res is None:
            return None

        return json.loads(res.decode('utf-8'))


def evaljs(code, **kwargs):
    """Evaluates the given ``code`` as JavaScript and returns the result"""
    return JSInterpreter().eval(code, **kwargs)