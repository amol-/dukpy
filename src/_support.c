#include <unistd.h>
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
    if (!PyCapsule_CheckExact(pyctx)) {
        return NULL;
    }

    duk_context *ctx = (duk_context*)PyCapsule_GetPointer(pyctx, CONTEXT_CAPSULE_NAME);
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
