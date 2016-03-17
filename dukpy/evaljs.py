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


def evaljs(code, **kwargs):
    """Evaluates the given ``code`` as JavaScript and returns the result"""
    jsvars = json.dumps(kwargs)
    jscode = code

    if not isinstance(code, string_types):
        jscode = ';\n'.join(code)

    res = _dukpy.eval_string(jscode, jsvars)
    if res is None:
        return None

    return json.loads(res.decode('utf-8'))
