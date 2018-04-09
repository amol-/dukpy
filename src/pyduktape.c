#include <stdlib.h>
#include <string.h>
#include <Python.h>
#include "duktape.h"
#include "_support.h"


#ifdef __cplusplus
extern "C" {
#endif

static PyObject *DukPyError;


static PyObject *DukPy_create_context(PyObject *self, PyObject *_) {
    duk_context *ctx = duk_create_heap(NULL, NULL, NULL, NULL, duktape_fatal_error_handler);
    if (!ctx) {
        PyErr_SetString(DukPyError, "Unable to create dukpy interpreter context");
        return NULL;
    }

    return make_capsule_for_context(ctx);
}


static PyObject *DukPy_eval_string(PyObject *self, PyObject *args) {
    PyObject *interpreter;
    PyObject *pyctx;
    duk_context *ctx;
    const char *command;
    const char *vars;
    int res;
    duk_int_t rc;
    const char *output;
    PyObject *result;

    if (!PyArg_ParseTuple(args, CONDITIONAL_PY3("Oyy", "Oss"), &interpreter, &command, &vars))
        return NULL;

    pyctx = PyObject_GetAttrString(interpreter, "_ctx");
    if (!pyctx) {
        PyErr_SetString(DukPyError, "Missing dukpy interpreter context");
        return NULL;
    }

    ctx = get_context_from_capsule(pyctx);
    if (!ctx) {
        PyErr_SetString(DukPyError, "Invalid dukpy interpreter context");
        return NULL;
    }

    duk_gc(ctx, 0);

    /* Save a reference to the JSInterpreter in the global stash */
    duk_push_global_stash(ctx);
    duk_push_pointer(ctx, interpreter);
    duk_put_prop_string(ctx, -2, "_py_interpreter");
    duk_pop(ctx);

    /* Make passed arguments available as the dukpy global object */
    duk_push_string(ctx, vars);
    duk_json_decode(ctx, -1);
    duk_put_global_string(ctx, "dukpy");

    /* Add a call_python function allows calling Python functions */
    duk_push_c_function(ctx, call_py_function, DUK_VARARGS);
    duk_put_global_string(ctx, "call_python");

    /* Add a _require_set_module_id which allows replacing id of loaded modules */
    duk_push_c_function(ctx, require_set_module_id, 2);
    duk_put_global_string(ctx, "_require_set_module_id");

    res = duk_peval_string(ctx, command);
    if (res != 0) {
        duk_get_prop_string(ctx, -1, "stack");
        PyErr_SetString(DukPyError, duk_safe_to_string(ctx, -1));
        duk_pop(ctx);
        return NULL;
    }

    rc = duk_safe_call(ctx, stack_json_encode, 1, 1);
    if (rc != DUK_EXEC_SUCCESS) {
        PyErr_SetString(DukPyError, duk_safe_to_string(ctx, -1));
        duk_pop(ctx);
        return NULL;
    }

    output = duk_get_string(ctx, -1);
    result = Py_BuildValue(CONDITIONAL_PY3("y", "s"), output);
    duk_pop(ctx);

    return result;
}


static PyMethodDef DukPy_methods[] = {
    {"eval_string", DukPy_eval_string, METH_VARARGS, "Run Javascript code from a string."},
    {"create_context", DukPy_create_context, METH_NOARGS, "Create an interpreter context where to run code"},
    {NULL, NULL, 0, NULL}
};

static char DukPy_doc[] = "Provides Javascript support to Python through the duktape library.";


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
init_dukpy()
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
