import json
from . import _dukpy

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

try:  # pragma: no cover
    unicode
    string_types = (str, unicode)
except NameError:  # pragma: no cover
    string_types = (bytes, str)


class JSInterpreter(object):
    """JavaScript Interpreter"""
    def __init__(self):
        self._ctx = _dukpy.create_context()

    def evaljs(self, code, **kwargs):
        """Runs JavaScript code in the context of the interpreter.

        All arguments will be converted to plain javascript objects
        through the JSON encoder and will be available in `dukpy`
        global object.

        Returns the last object on javascript stack.
        """
        jsvars = json.dumps(kwargs)
        jscode = code

        if not isinstance(code, string_types):
            jscode = ';\n'.join(code)

        if not isinstance(jscode, bytes):
            jscode = jscode.encode('utf-8')

        if not isinstance(jsvars, bytes):
            jsvars = jsvars.encode('utf-8')

        res = _dukpy.eval_string(self, jscode, jsvars)
        if res is None:
            return None

        return json.loads(res.decode('utf-8'))


def evaljs(code, **kwargs):
    """Evaluates the given ``code`` as JavaScript and returns the result"""
    return JSInterpreter().evaljs(code, **kwargs)