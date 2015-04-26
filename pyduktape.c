#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <Python.h>
#include "duktape.h"

#if PY_MAJOR_VERSION >= 3
#define CONDITIONAL_PY3(three, two) (three)
#else
#define CONDITIONAL_PY3(three, two) (two)
#endif

#ifdef __cplusplus
extern "C" {
#endif

static PyObject *DukPyError;

duk_ret_t stack_json_encode(duk_context *ctx) {
    const char *output = duk_json_encode(ctx, -1);
    duk_push_string(ctx, output);
    return 1;
}

static PyObject *DukPy_eval_string(PyObject *self, PyObject *args) {
    const char *command;
    const char *vars;

    if (!PyArg_ParseTuple(args, "ss", &command, &vars))
        return NULL;

    duk_context *ctx = duk_create_heap_default();
    if (ctx) {
        duk_push_string(ctx, vars);
        duk_json_decode(ctx, -1);
        duk_put_global_string(ctx, "dukpy");

        int res = duk_peval_string(ctx, command);
        if (res != 0) {
            PyErr_SetString(DukPyError, duk_safe_to_string(ctx, -1));
            return NULL;
        }
      
        duk_int_t rc = duk_safe_call(ctx, stack_json_encode, 1, 1);
        if (rc != DUK_EXEC_SUCCESS) { 
            PyErr_SetString(DukPyError, duk_safe_to_string(ctx, -1));
            return NULL;
        }

        const char *output = duk_get_string(ctx, -1);
        PyObject *result = Py_BuildValue(CONDITIONAL_PY3("y", "s"), output);
        duk_pop(ctx);
        duk_destroy_heap(ctx);
        return result;
    }


    Py_RETURN_NONE;
}


static PyMethodDef DukPy_methods[] = {
    {"eval_string", DukPy_eval_string, METH_VARARGS, "Run Javascript code from a string."},
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
