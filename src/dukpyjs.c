#include <stdlib.h>
#include <string.h>
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "quickjs.h"
#include "_support.h"

#include <stdio.h>

#ifdef __cplusplus
extern "C" {
#endif

static PyObject *DukPyError;

static PyObject *raise_js_exception(JSContext *ctx) {
    JSValue exception = JS_GetException(ctx);
    JSValue stack = JS_GetPropertyStr(ctx, exception, "stack");
    const char *message = NULL;

    if (!JS_IsUndefined(stack) && !JS_IsNull(stack)) {
        message = JS_ToCString(ctx, stack);
    }
    if (!message) {
        message = JS_ToCString(ctx, exception);
    }

    PyErr_SetString(DukPyError, message ? message : "JavaScript Error");
    if (message) {
        JS_FreeCString(ctx, message);
    }
    JS_FreeValue(ctx, stack);
    JS_FreeValue(ctx, exception);
    return NULL;
}

static PyObject *DukPy_create_context(PyObject *self, PyObject *_) {
    DukPyContext *ctx = calloc(1, sizeof(*ctx));
    if (!ctx) {
        PyErr_SetString(DukPyError, "Unable to allocate dukpy interpreter context");
        return NULL;
    }

    ctx->runtime = JS_NewRuntime();
    if (!ctx->runtime) {
        free(ctx);
        PyErr_SetString(DukPyError, "Unable to create QuickJS runtime");
        return NULL;
    }

    ctx->context = JS_NewContext(ctx->runtime);
    if (!ctx->context) {
        JS_FreeRuntime(ctx->runtime);
        free(ctx);
        PyErr_SetString(DukPyError, "Unable to create QuickJS context");
        return NULL;
    }

    JS_SetModuleLoaderFunc(ctx->runtime, dukpy_module_normalize, dukpy_module_loader, NULL);

    return make_capsule_for_context(ctx);
}


static PyObject *DukPy_eval_string(PyObject *self, PyObject *args) {
    PyObject *interpreter;
    PyObject *pyctx;
    DukPyContext *context;
    JSContext *ctx;
    const char *command;
    size_t command_len;
    const char *vars;
    size_t vars_len;
    const char *output;
    PyObject *result;
    JSValue eval_result;
    JSValue jsvars;
    JSValue json_result;
    JSValue global;

    if (!PyArg_ParseTuple(args, CONDITIONAL_PY3("Oy#y#", "Os#s#"), &interpreter,
                          &command, &command_len, &vars, &vars_len))
        return NULL;

    pyctx = PyObject_GetAttrString(interpreter, "_ctx");
    if (!pyctx) {
        PyErr_SetString(DukPyError, "Missing dukpy interpreter context");
        return NULL;
    }

    context = get_context_from_capsule(pyctx);

    if (!context) {
        PyErr_SetString(DukPyError, "Invalid dukpy interpreter context");
        Py_XDECREF(pyctx);
        return NULL;
    }

    ctx = context->context;
    JS_SetContextOpaque(ctx, interpreter);
    JS_RunGC(context->runtime);

    jsvars = JS_ParseJSON(ctx, vars, vars_len, "<dukpy>");
    if (JS_IsException(jsvars)) {
        Py_XDECREF(pyctx);
        return raise_js_exception(ctx);
    }

    global = JS_GetGlobalObject(ctx);
    JS_SetPropertyStr(ctx, global, "dukpy", jsvars);
    JS_SetPropertyStr(ctx, global, "call_python",
                      JS_NewCFunction(ctx, call_py_function, "call_python", 1));
    JS_SetPropertyStr(ctx, global, "_require_set_module_id",
                      JS_NewCFunction(ctx, require_set_module_id, "_require_set_module_id", 2));
    JS_FreeValue(ctx, global);

    if (JS_DetectModule(command, command_len)) {
        JSValue func_val = JS_Eval(ctx, command, command_len, "<dukpy>",
                                   JS_EVAL_TYPE_MODULE | JS_EVAL_FLAG_COMPILE_ONLY);
        if (JS_IsException(func_val)) {
            Py_XDECREF(pyctx);
            return raise_js_exception(ctx);
        }

        if (JS_ResolveModule(ctx, func_val) < 0) {
            JS_FreeValue(ctx, func_val);
            Py_XDECREF(pyctx);
            return raise_js_exception(ctx);
        }

        if (dukpy_module_set_import_meta(ctx, func_val, "<dukpy>", 1) < 0) {
            JS_FreeValue(ctx, func_val);
            Py_XDECREF(pyctx);
            return raise_js_exception(ctx);
        }

        eval_result = JS_EvalFunction(ctx, func_val);
    } else {
        eval_result = JS_Eval(ctx, command, command_len, "<dukpy>", JS_EVAL_TYPE_GLOBAL);
    }
    if (JS_IsException(eval_result)) {
        Py_XDECREF(pyctx);
        return raise_js_exception(ctx);
    }

    json_result = JS_JSONStringify(ctx, eval_result, JS_UNDEFINED, JS_UNDEFINED);
    JS_FreeValue(ctx, eval_result);
    if (JS_IsException(json_result)) {
        Py_XDECREF(pyctx);
        return raise_js_exception(ctx);
    }

    if (JS_IsNull(json_result)) {
        JS_FreeValue(ctx, json_result);
        json_result = JS_NewString(ctx, "{}");
    }

    if (JS_IsUndefined(json_result)) {
        JS_FreeValue(ctx, json_result);
        PyErr_SetString(DukPyError, "Invalid Result Value");
        Py_XDECREF(pyctx);
        return NULL;
    }

    output = JS_ToCString(ctx, json_result);
    JS_FreeValue(ctx, json_result);
    if (output == NULL) {
        PyErr_SetString(DukPyError, "Invalid Result Value");
        Py_XDECREF(pyctx);
        return NULL;
    }

    result = Py_BuildValue(CONDITIONAL_PY3("y", "s"), output);
    JS_FreeCString(ctx, output);
    Py_XDECREF(pyctx);

    return result;
}


static PyMethodDef DukPy_methods[] = {
    {"eval_string", DukPy_eval_string, METH_VARARGS, "Run Javascript code from a string."},
    {"create_context", DukPy_create_context, METH_NOARGS, "Create an interpreter context where to run code"},
    {NULL, NULL, 0, NULL}
};

static char DukPy_doc[] = "Provides Javascript support to Python through the QuickJS library.";


#if PY_MAJOR_VERSION >= 3

static struct PyModuleDef dukpymodule = {
    PyModuleDef_HEAD_INIT,
    "_dukpy",
    DukPy_doc,
    -1,
    DukPy_methods
};

PyMODINIT_FUNC 
PyInit__dukpy() 
{
    PyObject *module = PyModule_Create(&dukpymodule);
    if (module == NULL)
       return NULL;

    DukPyError = PyErr_NewException("_dukpy.JSRuntimeError", NULL, NULL);
    Py_INCREF(DukPyError);
    PyModule_AddObject(module, "JSRuntimeError", DukPyError);
    return module;
}

#else

PyMODINIT_FUNC 
init_dukpy(void)
{
    PyObject *module = Py_InitModule3("_dukpy", DukPy_methods, DukPy_doc);
    if (module == NULL)
       return;

    DukPyError = PyErr_NewException("_dukpy.JSRuntimeError", NULL, NULL);
    Py_INCREF(DukPyError);
    PyModule_AddObject(module, "JSRuntimeError", DukPyError);
}

#endif

#ifdef __cplusplus
}
#endif
