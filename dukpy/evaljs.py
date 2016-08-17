from __future__ import print_function
import json
import os
import logging

from dukpy.module_loader import JSModuleLoader
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


log = logging.getLogger('dukpy.interpreter')


class JSInterpreter(object):
    """JavaScript Interpreter"""
    def __init__(self):
        self._loader = JSModuleLoader()
        self._ctx = _dukpy.create_context()
        self._funcs = {}

        self._init_process()
        self._init_console()
        self._init_require()

    @property
    def loader(self):
        return self._loader

    def evaljs(self, code, **kwargs):
        """Runs JavaScript code in the context of the interpreter.

        All arguments will be converted to plain javascript objects
        through the JSON encoder and will be available in `dukpy`
        global object.

        Returns the last object on javascript stack.
        """
        jsvars = json.dumps(kwargs)
        jscode = self._adapt_code(code)

        if not isinstance(jscode, bytes):
            jscode = jscode.encode('utf-8')

        if not isinstance(jsvars, bytes):
            jsvars = jsvars.encode('utf-8')

        res = _dukpy.eval_string(self, jscode, jsvars)
        if res is None:
            return None

        return json.loads(res.decode('utf-8'))

    def export_function(self, name, func):
        """Exports a python function to the javascript layer with the given name.

        Note that it is possible to pass back and forth between JS and Python
        only plain javascript objects and that the objects are passed by
        copy so it is not possible to modify a python object from js.
        """
        self._funcs[name] = func

    def _call_python(self, func, json_args):
        # Arguments came in reverse order from JS
        func = func.decode('utf-8')
        json_args = json_args.decode('utf-8')

        args = list(reversed(json.loads(json_args)))
        ret = self._funcs[func](*args)
        if ret is not None:
            return json.dumps(ret).encode('utf-8')

    def _init_process(self):
        self.evaljs("process = {}; process.env = dukpy.environ", environ=dict(os.environ))

    def _init_console(self):
        self.export_function('dukpy.log.info', lambda *args: log.info(' '.join(args)))
        self.export_function('dukpy.log.error', lambda *args: log.error(' '.join(args)))
        self.export_function('dukpy.log.warn', lambda *args: log.warn(' '.join(args)))
        self.evaljs("""
        ;console = {
            log: function() {
                call_python('dukpy.log.info', Array.prototype.join.call(arguments, ' '));
            },
            info: function() {
                call_python('dukpy.log.info', Array.prototype.join.call(arguments, ' '));
            },
            warn: function() {
                call_python('dukpy.log.warn', Array.prototype.join.call(arguments, ' '));
            },
            error: function() {
                call_python('dukpy.log.error', Array.prototype.join.call(arguments, ' '));
            }
        };
        """)

    def _init_require(self):
        self.export_function('dukpy.lookup_module', self._loader.load)
        self.evaljs("""
        ;Duktape.modSearch = function (id, require, exports, module) {
            var m = call_python('dukpy.lookup_module', id);
            if (!m || !m[1]) {
                throw new Error('cannot find module: ' + id);
            }
            _require_set_module_id(require, m[0]);
            return m[1];
        };
""")

    def _adapt_code(self, code):
        def _read_files(f):
            if hasattr(f, 'read'):
                return f.read()
            else:
                return f

        code = _read_files(code)
        if not isinstance(code, string_types) and hasattr(code, '__iter__'):
            code = ';\n'.join(map(_read_files, code))
        return code


def evaljs(code, **kwargs):
    """Evaluates the given ``code`` as JavaScript and returns the result"""
    return JSInterpreter().evaljs(code, **kwargs)
