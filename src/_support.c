#include <stdlib.h>
#include <string.h>
#include <Python.h>
#include "capsulethunk.h"
#include "duktape.h"
#include "_support.h"

static char const * const CONTEXT_CAPSULE_NAME = "DUKPY_CONTEXT_CAPSULE";


duk_ret_t stack_json_encode(duk_context *ctx) {
    const char *output = duk_json_encode(ctx, -1);
    duk_push_string(ctx, output);
    return 1;
}


duk_context *get_context_from_capsule(PyObject* pyctx) {
    duk_context *ctx = NULL;

    if (!PyCapsule_CheckExact(pyctx)) {
        return NULL;
    }

    ctx = (duk_context*)PyCapsule_GetPointer(pyctx, CONTEXT_CAPSULE_NAME);
    if (!ctx) {
        return NULL;
    }

    return ctx;
}


void duktape_fatal_error_handler(duk_context *ctx, duk_errcode_t code, const char *msg) {
    PyErr_SetString(PyExc_RuntimeError, msg);
}


void context_destroy(PyObject* pyctx) {
    duk_context *ctx = get_context_from_capsule(pyctx);
    if (!ctx)
        return;

    duk_destroy_heap(ctx);
}


PyObject *make_capsule_for_context(duk_context *ctx) {
    return PyCapsule_New(ctx, CONTEXT_CAPSULE_NAME, &context_destroy);
}


int call_py_function(duk_context *ctx) {
    char const *args;
    char const *pyfuncname;
    int i;
    int args_count = duk_get_top(ctx);
    PyObject *interpreter;
    PyObject *ret;

    /* Create array to contain all function arguments */
    duk_push_array(ctx);
    for(i=0; i<args_count-1; i++) {
        duk_swap_top(ctx, -2);
        duk_put_prop_index(ctx, -2, i);
    }
    args = duk_json_encode(ctx, -1);
    pyfuncname = duk_get_string(ctx, -2);

    duk_push_global_stash(ctx);
    duk_get_prop_string(ctx, -1, "_py_interpreter");
    interpreter = duk_get_pointer(ctx, -1);
    duk_pop(ctx);
    duk_pop(ctx);

    ret = PyObject_CallMethod(interpreter, "_call_python", CONDITIONAL_PY3("yy", "ss"),
                              pyfuncname, args);

    /* Pop array of argumnets and method name */
    duk_pop(ctx);
    duk_pop(ctx);

    if (ret == NULL) {
        PyObject *error = NULL;
        char const *strerror = "Unknown Error";
        PyObject *ptype, *pvalue, *ptraceback, *error_repr;
        
        PyErr_Fetch(&ptype, &pvalue, &ptraceback);
        error_repr = PyObject_Repr(pvalue);
        if (PyUnicode_Check(error_repr)) {
            error = PyUnicode_AsEncodedString(error_repr, "UTF-8", "replace");
            strerror = PyBytes_AsString(error);
        }
        else if (PyBytes_Check(error_repr)) {
            strerror = PyBytes_AsString(error_repr);
        }

        duk_push_error_object(ctx, DUK_ERR_EVAL_ERROR,
                              "Error while calling Python Function: %s", strerror);

        Py_XDECREF(error_repr);
        Py_XDECREF(ptype);
        Py_XDECREF(ptraceback);
        Py_XDECREF(pvalue);
        Py_XDECREF(error);

        duk_throw(ctx);
    }

    if (ret == Py_None)
        return 0;

    duk_push_string(ctx, PyBytes_AsString(ret));
    duk_json_decode(ctx, -1);
    Py_XDECREF(ret);
    return 1;
}


int require_set_module_id(duk_context *ctx) {
    duk_push_string(ctx, "id");
    duk_swap(ctx, -1, -2);
    duk_def_prop(ctx, -3, DUK_DEFPROP_HAVE_VALUE|DUK_DEFPROP_FORCE);
    duk_pop(ctx);
    return 0;
}
