from __future__ import print_function
import json
import os
import logging
import posixpath

from dukpy.module_loader import JSModuleLoader
from . import _dukpy

try:
    from collections.abc import Iterable
except ImportError:  # pragma: no cover
    from collections import Iterable

try:  # pragma: no cover
    unicode
    string_types = (str, unicode)
except NameError:  # pragma: no cover
    string_types = (bytes, str)


log = logging.getLogger("dukpy.interpreter")


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
            jscode = jscode.encode("utf-8")

        if not isinstance(jsvars, bytes):
            jsvars = jsvars.encode("utf-8")

        res = _dukpy.eval_string(self, jscode, jsvars)
        if res is None:
            return None

        return json.loads(res.decode("utf-8"))

    def export_function(self, name, func):
        """Exports a python function to the javascript layer with the given name.

        Note that it is possible to pass back and forth between JS and Python
        only plain javascript objects and that the objects are passed by
        copy so it is not possible to modify a python object from js.
        """
        self._funcs[name] = func

    def _check_exported_function_exists(self, func):
        func = func.decode("ascii")
        return func in self._funcs

    def _call_python(self, func, json_args):
        # Arguments came in reverse order from JS
        func = func.decode("ascii")
        json_args = json_args.decode("utf-8")

        args = list(reversed(json.loads(json_args)))
        ret = self._funcs[func](*args)
        if ret is not None:
            return json.dumps(ret).encode("utf-8")

    def _init_process(self):
        self.evaljs(
            "process = {}; process.env = dukpy.environ", environ=dict(os.environ)
        )

    def _init_console(self):
        self.export_function("dukpy.log.info", lambda *args: log.info(" ".join(args)))
        self.export_function("dukpy.log.error", lambda *args: log.error(" ".join(args)))
        self.export_function("dukpy.log.warn", lambda *args: log.warn(" ".join(args)))
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
        self.export_function("dukpy.load_module", self._load_module)
        self.export_function("dukpy.normalize_module", self._normalize_module)
        self.evaljs("""
        ;(function() {
            var _dukpy_modules = {};
            function _dukpy_make_require(base) {
                function _dukpy_require(id) {
                    var resolved = call_python('dukpy.normalize_module', base || '', id) || id;
                    if (_dukpy_modules[resolved]) {
                        return _dukpy_modules[resolved].exports;
                    }
                    var m = call_python('dukpy.load_module', resolved);
                    if (!m || !m[1]) {
                        throw new Error('cannot find module: ' + id);
                    }
                    var module = { id: m[0], exports: {} };
                    _dukpy_modules[module.id] = module;
                    if (module.id !== resolved) {
                        _dukpy_modules[resolved] = module;
                    }
                    module.require = _dukpy_make_require(module.id);
                    var exports = module.exports;
                    var func = new Function('require', 'exports', 'module', m[1]);
                    func(module.require, exports, module);
                    return module.exports;
                }
                _dukpy_require.id = base || '';
                return _dukpy_require;
            }
            globalThis.require = _dukpy_make_require('');
        })();
""")

    def _normalize_module(self, base_name, module_name):
        if module_name.startswith(".") and base_name:
            base_dir = base_name.rsplit("/", 1)[0] if "/" in base_name else base_name
            module_name = posixpath.normpath(posixpath.join(base_dir, module_name))
        module_id, _ = self._loader.lookup(module_name)
        return module_id or module_name

    def _load_module(self, module_name):
        return self._loader.load(module_name)

    def _adapt_code(self, code):
        def _read_files(f):
            if hasattr(f, "read"):
                return f.read()
            else:
                return f

        code = _read_files(code)
        if not isinstance(code, string_types) and hasattr(code, "__iter__"):
            code = ";\n".join(map(_read_files, code))
        return code


def evaljs(code, **kwargs):
    """Evaluates the given ``code`` as JavaScript and returns the result"""
    return JSInterpreter().evaljs(code, **kwargs)
