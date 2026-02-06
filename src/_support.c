#include <stdlib.h>
#include <string.h>
#include <Python.h>
#include "capsulethunk.h"
#include "_support.h"

static char const * const CONTEXT_CAPSULE_NAME = "DUKPY_CONTEXT_CAPSULE";


DukPyContext *get_context_from_capsule(PyObject *pyctx) {
    if (!PyCapsule_CheckExact(pyctx)) {
        return NULL;
    }

    return (DukPyContext *)PyCapsule_GetPointer(pyctx, CONTEXT_CAPSULE_NAME);
}


void context_destroy(PyObject* pyctx) {
    DukPyContext *ctx = get_context_from_capsule(pyctx);
    if (!ctx) {
        return;
    }

    if (ctx->context) {
        JS_FreeContext(ctx->context);
    }
    if (ctx->runtime) {
        JS_FreeRuntime(ctx->runtime);
    }
    free(ctx);
}


PyObject *make_capsule_for_context(DukPyContext *ctx) {
    return PyCapsule_New(ctx, CONTEXT_CAPSULE_NAME, &context_destroy);
}


JSValue call_py_function(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv) {
    JSValue args_array;
    JSValue json_args;
    JSValue parsed;
    PyObject *interpreter = (PyObject *)JS_GetContextOpaque(ctx);
    PyObject *ret;
    const char *args;
    const char *pyfuncname;

    if (!interpreter) {
        return JS_ThrowReferenceError(ctx, "Missing dukpy interpreter");
    }
    if (argc < 1) {
        return JS_ThrowTypeError(ctx, "call_python expects a function name");
    }

    pyfuncname = JS_ToCString(ctx, argv[0]);
    if (!pyfuncname) {
        return JS_EXCEPTION;
    }

    args_array = JS_NewArray(ctx);
    for (int i = 1; i < argc; i++) {
        JS_SetPropertyUint32(ctx, args_array, (uint32_t)(i - 1), JS_DupValue(ctx, argv[i]));
    }

    json_args = JS_JSONStringify(ctx, args_array, JS_UNDEFINED, JS_UNDEFINED);
    JS_FreeValue(ctx, args_array);
    if (JS_IsException(json_args)) {
        JS_FreeCString(ctx, pyfuncname);
        return JS_EXCEPTION;
    }

    args = JS_ToCString(ctx, json_args);
    JS_FreeValue(ctx, json_args);
    if (!args) {
        JS_FreeCString(ctx, pyfuncname);
        return JS_EXCEPTION;
    }

    ret = PyObject_CallMethod(interpreter, "_check_exported_function_exists",
                              CONDITIONAL_PY3("y", "s"), pyfuncname);
    if (ret == NULL) {
        JSValue exception = JS_ThrowInternalError(ctx, "Failed to resolve Python function %s",
                                                  pyfuncname);
        JS_FreeCString(ctx, args);
        JS_FreeCString(ctx, pyfuncname);
        return exception;
    }
    if (ret == Py_False) {
        Py_DECREF(ret);
        JS_FreeCString(ctx, args);
        JS_FreeCString(ctx, pyfuncname);
        return JS_ThrowReferenceError(ctx, "No Python Function named %s", pyfuncname);
    }
    Py_DECREF(ret);

    ret = PyObject_CallMethod(interpreter, "_call_python", CONDITIONAL_PY3("yy", "ss"),
                              pyfuncname, args);
    JS_FreeCString(ctx, args);

    if (ret == NULL) {
        PyObject *error = NULL;
        char const *strerror = "Unknown Error";
        PyObject *ptype, *pvalue, *ptraceback, *error_repr;

        PyErr_Fetch(&ptype, &pvalue, &ptraceback);
        error_repr = PyObject_Repr(pvalue);
        if (PyUnicode_Check(error_repr)) {
            error = PyUnicode_AsEncodedString(error_repr, "UTF-8", "replace");
            strerror = PyBytes_AsString(error);
        } else if (PyBytes_Check(error_repr)) {
            strerror = PyBytes_AsString(error_repr);
        }

        JSValue exception = JS_ThrowInternalError(ctx,
                                                  "Error while calling Python Function (%s): %s",
                                                  pyfuncname, strerror);
        Py_XDECREF(error_repr);
        Py_XDECREF(ptype);
        Py_XDECREF(ptraceback);
        Py_XDECREF(pvalue);
        Py_XDECREF(error);
        JS_FreeCString(ctx, pyfuncname);
        return exception;
    }

    if (ret == Py_None) {
        Py_DECREF(ret);
        JS_FreeCString(ctx, pyfuncname);
        return JS_UNDEFINED;
    }

    parsed = JS_ParseJSON(ctx, PyBytes_AsString(ret), PyBytes_GET_SIZE(ret), "<python>");
    Py_DECREF(ret);
    JS_FreeCString(ctx, pyfuncname);
    if (JS_IsException(parsed)) {
        return JS_EXCEPTION;
    }

    return parsed;
}


JSValue require_set_module_id(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv) {
    if (argc < 2) {
        return JS_UNDEFINED;
    }

    JS_SetPropertyStr(ctx, argv[0], "id", JS_DupValue(ctx, argv[1]));
    return JS_UNDEFINED;
}

char *dukpy_module_normalize(JSContext *ctx, const char *module_base_name,
                             const char *module_name, void *opaque) {
    PyObject *interpreter = (PyObject *)JS_GetContextOpaque(ctx);
    PyObject *normalized = NULL;
    const char *normalized_c;
    Py_ssize_t normalized_len;
    char *result;

    if (!interpreter) {
        JS_ThrowReferenceError(ctx, "Missing dukpy interpreter");
        return NULL;
    }

    normalized = PyObject_CallMethod(interpreter, "_normalize_module", "ss",
                                     module_base_name ? module_base_name : "",
                                     module_name);
    if (!normalized) {
        PyErr_Clear();
        JS_ThrowInternalError(ctx, "Failed to normalize module '%s'", module_name);
        return NULL;
    }

    normalized_c = PyUnicode_AsUTF8AndSize(normalized, &normalized_len);
    if (!normalized_c) {
        Py_DECREF(normalized);
        PyErr_Clear();
        JS_ThrowInternalError(ctx, "Invalid normalized module name");
        return NULL;
    }

    result = js_malloc(ctx, (size_t)normalized_len + 1);
    if (!result) {
        Py_DECREF(normalized);
        return NULL;
    }

    memcpy(result, normalized_c, (size_t)normalized_len);
    result[normalized_len] = '\0';
    Py_DECREF(normalized);
    return result;
}

int dukpy_module_set_import_meta(JSContext *ctx, JSValueConst func_val,
                                 const char *module_name, int is_main) {
    JSModuleDef *module;
    JSValue meta_obj;

    if (JS_VALUE_GET_TAG(func_val) != JS_TAG_MODULE) {
        return -1;
    }

    module = JS_VALUE_GET_PTR(func_val);
    meta_obj = JS_GetImportMeta(ctx, module);
    if (JS_IsException(meta_obj)) {
        return -1;
    }

    JS_DefinePropertyValueStr(ctx, meta_obj, "url", JS_NewString(ctx, module_name),
                              JS_PROP_C_W_E);
    JS_DefinePropertyValueStr(ctx, meta_obj, "main", JS_NewBool(ctx, is_main),
                              JS_PROP_C_W_E);
    JS_FreeValue(ctx, meta_obj);
    return 0;
}

JSModuleDef *dukpy_module_loader(JSContext *ctx, const char *module_name, void *opaque) {
    PyObject *interpreter = (PyObject *)JS_GetContextOpaque(ctx);
    PyObject *loaded = NULL;
    PyObject *module_id = NULL;
    PyObject *source = NULL;
    const char *module_id_c;
    const char *source_c;
    Py_ssize_t source_len;
    JSValue func_val;
    JSModuleDef *module;

    if (!interpreter) {
        JS_ThrowReferenceError(ctx, "Missing dukpy interpreter");
        return NULL;
    }

    loaded = PyObject_CallMethod(interpreter, "_load_module", "s", module_name);
    if (!loaded) {
        PyErr_Clear();
        JS_ThrowInternalError(ctx, "Failed to load module '%s'", module_name);
        return NULL;
    }

    if (!PyTuple_Check(loaded) || PyTuple_GET_SIZE(loaded) < 2) {
        Py_DECREF(loaded);
        JS_ThrowTypeError(ctx, "Invalid module loader response");
        return NULL;
    }

    module_id = PyTuple_GET_ITEM(loaded, 0);
    source = PyTuple_GET_ITEM(loaded, 1);
    if (module_id == Py_None || source == Py_None) {
        Py_DECREF(loaded);
        JS_ThrowReferenceError(ctx, "cannot find module: %s", module_name);
        return NULL;
    }

    module_id_c = PyUnicode_AsUTF8(module_id);
    if (!module_id_c) {
        Py_DECREF(loaded);
        PyErr_Clear();
        JS_ThrowInternalError(ctx, "Invalid module id");
        return NULL;
    }

    if (PyBytes_Check(source)) {
        if (PyBytes_AsStringAndSize(source, (char **)&source_c, &source_len) < 0) {
            Py_DECREF(loaded);
            PyErr_Clear();
            JS_ThrowInternalError(ctx, "Invalid module source");
            return NULL;
        }
    } else {
        source_c = PyUnicode_AsUTF8AndSize(source, &source_len);
        if (!source_c) {
            Py_DECREF(loaded);
            PyErr_Clear();
            JS_ThrowInternalError(ctx, "Invalid module source");
            return NULL;
        }
    }

    func_val = JS_Eval(ctx, source_c, source_len, module_id_c,
                       JS_EVAL_TYPE_MODULE | JS_EVAL_FLAG_COMPILE_ONLY);
    if (JS_IsException(func_val)) {
        Py_DECREF(loaded);
        return NULL;
    }

    if (dukpy_module_set_import_meta(ctx, func_val, module_id_c, 0) < 0) {
        JS_FreeValue(ctx, func_val);
        Py_DECREF(loaded);
        return NULL;
    }

    module = JS_VALUE_GET_PTR(func_val);
    JS_FreeValue(ctx, func_val);
    Py_DECREF(loaded);
    return module;
}
