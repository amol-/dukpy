from __future__ import print_function
import json
import os
import logging
import posixpath

from dukpy.module_loader import JSModuleLoader
from . import _dukpy

string_types = (bytes, str)
_RUNTIME_DIR = os.path.join(os.path.dirname(__file__), "jsruntime")
_PROCESS_RUNTIME = os.path.join(_RUNTIME_DIR, "process_runtime.js")
_CONSOLE_RUNTIME = os.path.join(_RUNTIME_DIR, "console_runtime.js")
_COMMONJS_RUNTIME = os.path.join(_RUNTIME_DIR, "commonjs_runtime.js")


log = logging.getLogger("dukpy.interpreter")


class JSInterpreter(object):
    """Persistent QuickJS-backed interpreter.

    This Python boundary adapts host inputs: code may be read from files or the
    legacy iterable form, keyword arguments are JSON-encoded onto the JavaScript
    ``dukpy`` global, and JSON results are decoded back to Python values.
    JavaScript syntax decisions stay below this layer: ``_dukpy.eval_string``
    receives the source bytes plus the explicit script/module mode and delegates
    parsing, module compilation, evaluation, job draining, and result
    serialization to QuickJS.
    """

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
        """Run JavaScript code as a global script in this interpreter.

        All arguments are converted to plain JavaScript values through the JSON
        encoder and are available on the ``dukpy`` global object. Python does not
        inspect ``code`` to classify JavaScript syntax; QuickJS parses and
        evaluates it as a script.
        """
        return self._evaljs(code, False, "<dukpy>", kwargs)

    def evaljs_module(self, code, module_name="<dukpy>", **kwargs):
        """Run JavaScript code as a native ES module in this interpreter.

        The module name is passed to QuickJS for ``import.meta.url`` and as the
        base for resolving top-level relative imports. All user data keyword
        arguments are converted to plain JavaScript values through the JSON
        encoder and are available on the ``dukpy`` global object. This explicit
        module API keeps ``evaljs`` keyword arguments reserved for user data and
        avoids Python-side source scanning for module syntax.
        """
        return self._evaljs(code, True, module_name, kwargs)

    def _evaljs(self, code, eval_as_module, module_name, kwargs):
        """Adapt Python values, then cross the native QuickJS boundary."""
        jsvars = json.dumps(kwargs)
        jscode = self._adapt_code(code)

        if not isinstance(jscode, bytes):
            jscode = jscode.encode("utf-8")

        if not isinstance(jsvars, bytes):
            jsvars = jsvars.encode("utf-8")

        res = _dukpy.eval_string(self, jscode, jsvars, eval_as_module, module_name)
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
        func = func.decode("utf-8")
        return func in self._funcs

    def _call_python(self, func, json_args):
        func = func.decode("utf-8")
        json_args = json_args.decode("utf-8")

        args = json.loads(json_args)
        ret = self._funcs[func](*args)
        if ret is not None:
            return json.dumps(ret).encode("utf-8")

    def _init_process(self):
        self._eval_runtime_shim(_PROCESS_RUNTIME, environ=dict(os.environ))

    def _init_console(self):
        self.export_function("dukpy.log.info", lambda *args: log.info(" ".join(args)))
        self.export_function("dukpy.log.error", lambda *args: log.error(" ".join(args)))
        self.export_function("dukpy.log.warn", lambda *args: log.warn(" ".join(args)))
        self._eval_runtime_shim(_CONSOLE_RUNTIME)

    def _init_require(self):
        self.export_function("dukpy.load_module", self._loader.load)
        self.export_function("dukpy.normalize_module", self._normalize_module)
        self._eval_runtime_shim(_COMMONJS_RUNTIME)

    def _eval_runtime_shim(self, path, **kwargs):
        """Evaluate a reviewed host-runtime JavaScript asset."""
        with open(path, encoding="utf-8") as runtime:
            self.evaljs(runtime, **kwargs)

    def _normalize_module(self, base_name, module_name):
        if module_name.startswith(".") and base_name:
            base_dir = base_name.rsplit("/", 1)[0] if "/" in base_name else ""
            module_name = posixpath.normpath(posixpath.join(base_dir, module_name))
        module_id, _ = self._loader.lookup(module_name)
        return module_id or module_name

    def _adapt_code(self, code):
        """Adapt legacy source containers without interpreting JavaScript.

        File-like objects are read once. Iterable input is the historical DukPy
        compatibility form: each fragment is read if needed, the fragments are
        joined with ``;\n``, and QuickJS then parses the combined script. The
        inserted semicolon is part of the public legacy contract rather than a
        JavaScript syntax decision made by Python.
        """
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
    """Evaluate ``code`` as a QuickJS global script in a fresh interpreter.

    Python adapts inputs and JSON keyword data, then the native QuickJS boundary
    parses, evaluates, drains jobs, and serializes the result.
    """
    return JSInterpreter().evaljs(code, **kwargs)


def evaljs_module(code, module_name="<dukpy>", **kwargs):
    """Evaluate ``code`` as a QuickJS native ES module in a fresh interpreter.

    ``module_name`` is explicit host intent for QuickJS; Python does not scan
    source text to infer module syntax.
    """
    return JSInterpreter().evaljs_module(code, module_name=module_name, **kwargs)
