#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <Python.h>
#include "_support.h"

static char const * const CONTEXT_CAPSULE_NAME = "DUKPY_CONTEXT_CAPSULE";


/* Accept only the private capsule name so arbitrary Python objects cannot be
 * mistaken for a live QuickJS context. */
DukPyContext *get_context_from_capsule(PyObject *pyctx) {
    if (!PyCapsule_CheckExact(pyctx)) {
        return NULL;
    }

    return (DukPyContext *)PyCapsule_GetPointer(pyctx, CONTEXT_CAPSULE_NAME);
}


/* PyCapsule destructor: free QuickJS values before their owning context/runtime. */
void context_destroy(PyObject* pyctx) {
    DukPyContext *ctx = get_context_from_capsule(pyctx);
    DukPyRejectedPromise *rejection;
    if (!ctx) {
        return;
    }

    rejection = ctx->rejected_promises;
    while (rejection) {
        DukPyRejectedPromise *next = rejection->next;
        if (ctx->context) {
            JS_FreeValue(ctx->context, rejection->promise);
            JS_FreeValue(ctx->context, rejection->reason);
        }
        free(rejection);
        rejection = next;
    }

    if (ctx->context) {
        JS_FreeContext(ctx->context);
    }
    if (ctx->runtime) {
        JS_FreeRuntime(ctx->runtime);
    }
    free(ctx);
}


/* Hand the C context to Python with the only destructor that owns it. */
PyObject *make_capsule_for_context(DukPyContext *ctx) {
    return PyCapsule_New(ctx, CONTEXT_CAPSULE_NAME, &context_destroy);
}


/* JavaScript-to-Python callback bridge installed as global call_python.
 *
 * JSON is the intentional language boundary in both directions. It matches the
 * public evaljs contract, keeps JavaScript and Python object ownership isolated,
 * and gives callbacks copy-by-value data instead of live cross-runtime handles.
 * The bridge therefore has JSON.stringify/json.loads/json.dumps limits: BigInt
 * and cycles fail, object properties that are undefined/functions/symbols are
 * omitted, those array entries become null, NaN/Infinity become null on the
 * JavaScript-to-Python path, and Python callbacks must return values that encode
 * as JSON bytes QuickJS can parse. A Python None return is the one host-side
 * sentinel; it maps to JavaScript undefined.
 *
 * Boundary failures are translated where they occur: missing Python exports are
 * JavaScript ReferenceError, Python callable or Python JSON encoding failures are
 * catchable JavaScript InternalError, and QuickJS JSON parse/stringify failures
 * stay as the current JavaScript exception. */
JSValue call_py_function(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv) {
    JSValue args_array;
    JSValue json_args;
    JSValue parsed;
    PyObject *interpreter = (PyObject *)JS_GetContextOpaque(ctx);
    PyObject *pyctx;
    PyObject *ret;
    DukPyContext *dukpy_ctx;
    const char *args;
    const char *pyfuncname;

    if (!interpreter) {
        return JS_ThrowReferenceError(ctx, "Missing dukpy interpreter");
    }

    pyctx = PyObject_GetAttrString(interpreter, "_ctx");
    if (!pyctx) {
        PyErr_Clear();
        return JS_ThrowReferenceError(ctx, "Missing dukpy interpreter context");
    }
    dukpy_ctx = get_context_from_capsule(pyctx);
    Py_DECREF(pyctx);
    if (!dukpy_ctx) {
        PyErr_Clear();
        return JS_ThrowReferenceError(ctx, "Invalid dukpy interpreter context");
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

    if (dukpy_should_interrupt()) {
        JS_FreeCString(ctx, args);
        JS_FreeCString(ctx, pyfuncname);
        return JS_ThrowInternalError(ctx, "interrupted");
    }

    ret = PyObject_CallMethod(interpreter, "_check_exported_function_exists", "y", pyfuncname);
    if (ret == NULL) {
        PyObject *ptype, *pvalue, *ptraceback;
        PyErr_Fetch(&ptype, &pvalue, &ptraceback);
        Py_XDECREF(ptype);
        Py_XDECREF(pvalue);
        Py_XDECREF(ptraceback);
        JSValue exception = JS_ThrowInternalError(ctx, "Failed to resolve Python function %s",
                                                  pyfuncname);
        JS_FreeCString(ctx, args);
        JS_FreeCString(ctx, pyfuncname);
        return exception;
    }
    if (ret == Py_False) {
        JSValue exception = JS_ThrowReferenceError(ctx, "No Python Function named %s",
                                                  pyfuncname);
        Py_DECREF(ret);
        JS_FreeCString(ctx, args);
        JS_FreeCString(ctx, pyfuncname);
        return exception;
    }
    Py_DECREF(ret);

    /* _call_python decodes JSON args, runs the exported callable, and JSON-encodes
     * its return; any Python failure here becomes a catchable JavaScript error. */
    ret = PyObject_CallMethod(interpreter, "_call_python", "yy", pyfuncname, args);
    JS_FreeCString(ctx, args);

    if (ret != NULL && dukpy_should_interrupt()) {
        Py_DECREF(ret);
        JS_FreeCString(ctx, pyfuncname);
        return JS_ThrowInternalError(ctx, "interrupted");
    }

    if (ret == NULL) {
        PyObject *error = NULL;
        char const *strerror = "Unknown Error";
        PyObject *ptype, *pvalue, *ptraceback, *error_repr;

        PyErr_Fetch(&ptype, &pvalue, &ptraceback);
        error_repr = NULL;
        if (pvalue || ptype) {
            error_repr = PyObject_Repr(pvalue ? pvalue : ptype);
        }
        if (error_repr) {
            if (PyUnicode_Check(error_repr)) {
                error = PyUnicode_AsEncodedString(error_repr, "UTF-8", "replace");
                if (error) {
                    char const *encoded_error = PyBytes_AsString(error);
                    if (encoded_error) {
                        strerror = encoded_error;
                    }
                }
            } else if (PyBytes_Check(error_repr)) {
                char const *bytes_error = PyBytes_AsString(error_repr);
                if (bytes_error) {
                    strerror = bytes_error;
                }
            }
        }

        JSValue exception = JS_ThrowInternalError(ctx,
                                                  "Error while calling Python Function (%s): %s",
                                                  pyfuncname, strerror);
        Py_XDECREF(error_repr);
        Py_XDECREF(ptype);
        Py_XDECREF(ptraceback);
        Py_XDECREF(pvalue);
        Py_XDECREF(error);
        PyErr_Clear();
        JS_FreeCString(ctx, pyfuncname);
        return exception;
    }

    if (ret == Py_None) {
        Py_DECREF(ret);
        JS_FreeCString(ctx, pyfuncname);
        return JS_UNDEFINED;
    }

    /* Re-enter QuickJS through JSON so callback returns obey the same value
     * limits as arguments and evaljs results. */
    parsed = JS_ParseJSON(ctx, PyBytes_AsString(ret), PyBytes_GET_SIZE(ret), "<python>");
    Py_DECREF(ret);
    JS_FreeCString(ctx, pyfuncname);
    if (JS_IsException(parsed)) {
        return JS_EXCEPTION;
    }

    return parsed;
}


/* QuickJS asks this callback for canonical module names; Python owns package
 * metadata and path rules, while C returns a js_malloc-owned string. */
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

/* Attach only DukPy's public import.meta contract to a compiled module. */
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

/* CommonJS-to-ESM interop is intentionally a narrow synthetic namespace:
   default, module, exports, and require. It is only reached for loader-classified
   CommonJS modules; native ES modules stay on the QuickJS module path. */
/* Failed QuickJS modules stay cached, so CommonJS wrappers use unique names
 * while import.meta.url continues to expose the real module id. */
static char *dukpy_commonjs_wrapper_name(const char *module_id, unsigned long wrapper_id) {
    static const char marker[] = "?dukpy-commonjs-wrapper=";
    char suffix[sizeof(unsigned long) * 3 + 1];
    int suffix_len = snprintf(suffix, sizeof(suffix), "%lu", wrapper_id);
    size_t module_len;
    size_t len;
    char *name;

    if (suffix_len < 0 || (size_t)suffix_len >= sizeof(suffix)) {
        return NULL;
    }

    module_len = strlen(module_id);
    len = module_len + (sizeof(marker) - 1) + (size_t)suffix_len;
    name = malloc(len + 1);
    if (!name) {
        return NULL;
    }

    snprintf(name, len + 1, "%s%s%s", module_id, marker, suffix);
    return name;
}

/* Pass the original CommonJS source through import.meta for the JavaScript
 * wrapper; the wrapper, not C, evaluates CommonJS semantics. */
static int dukpy_module_set_commonjs_import_meta(JSContext *ctx, JSValueConst func_val,
                                                  const char *module_name,
                                                  JSValueConst commonjs_source) {
    JSModuleDef *module;
    JSValue meta_obj;

    if (dukpy_module_set_import_meta(ctx, func_val, module_name, 0) < 0) {
        return -1;
    }

    module = JS_VALUE_GET_PTR(func_val);
    meta_obj = JS_GetImportMeta(ctx, module);
    if (JS_IsException(meta_obj)) {
        return -1;
    }

    if (JS_DefinePropertyValueStr(ctx, meta_obj, "dukpyCommonJsSource",
                                  JS_DupValue(ctx, commonjs_source), JS_PROP_C_W_E) < 0) {
        JS_FreeValue(ctx, meta_obj);
        return -1;
    }
    JS_FreeValue(ctx, meta_obj);
    return 0;
}

/* Synthetic ES module that exposes the intentionally small CommonJS namespace. */
static const char dukpy_commonjs_module_wrapper[] =
    "const module = globalThis._dukpy_eval_cjs_source("
    "import.meta.url, import.meta.url, import.meta.dukpyCommonJsSource);\n"
    "const exports = module.exports;\n"
    "const require = module.require;\n"
    "export default module.exports;\n"
    "export { module, exports, require };\n";

/* QuickJS module loader boundary: Python returns (id, source, format), then C
 * compiles either native ESM or a narrow CommonJS wrapper without parsing JS. */
JSModuleDef *dukpy_module_loader(JSContext *ctx, const char *module_name, void *opaque) {
    PyObject *interpreter = (PyObject *)JS_GetContextOpaque(ctx);
    PyObject *loaded = NULL;
    PyObject *module_id = NULL;
    PyObject *source = NULL;
    PyObject *module_format = NULL;
    const char *module_id_c;
    const char *source_c;
    const char *module_format_c;
    const char *eval_source_c;
    const char *eval_module_name_c;
    char *commonjs_wrapper_name = NULL;
    Py_ssize_t source_len;
    size_t eval_source_len;
    JSValue commonjs_source = JS_UNDEFINED;
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

    if (!PyTuple_Check(loaded) || PyTuple_GET_SIZE(loaded) < 3) {
        Py_DECREF(loaded);
        JS_ThrowTypeError(ctx, "Invalid module loader response");
        return NULL;
    }

    module_id = PyTuple_GET_ITEM(loaded, 0);
    source = PyTuple_GET_ITEM(loaded, 1);
    module_format = PyTuple_GET_ITEM(loaded, 2);
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

    module_format_c = PyUnicode_AsUTF8(module_format);
    if (!module_format_c) {
        Py_DECREF(loaded);
        PyErr_Clear();
        JS_ThrowTypeError(ctx, "Invalid module format");
        return NULL;
    }

    eval_source_c = source_c;
    eval_module_name_c = module_id_c;
    eval_source_len = (size_t)source_len;
    if (strcmp(module_format_c, "commonjs") == 0) {
        PyObject *pyctx = PyObject_GetAttrString(interpreter, "_ctx");
        DukPyContext *dukpy_ctx = pyctx ? get_context_from_capsule(pyctx) : NULL;
        unsigned long wrapper_id;

        Py_XDECREF(pyctx);
        if (!dukpy_ctx) {
            PyErr_Clear();
            Py_DECREF(loaded);
            JS_ThrowInternalError(ctx, "Invalid dukpy interpreter context");
            return NULL;
        }

        /* QuickJS keeps failed modules cached; CommonJS body/cache semantics live in
           _dukpy_eval_cjs_source, so each synthetic wrapper gets a disposable name. */
        wrapper_id = ++dukpy_ctx->next_commonjs_wrapper_id;
        if (wrapper_id == 0) {
            wrapper_id = ++dukpy_ctx->next_commonjs_wrapper_id;
        }
        commonjs_wrapper_name = dukpy_commonjs_wrapper_name(module_id_c, wrapper_id);
        if (!commonjs_wrapper_name) {
            Py_DECREF(loaded);
            JS_ThrowOutOfMemory(ctx);
            return NULL;
        }
        eval_source_c = dukpy_commonjs_module_wrapper;
        eval_module_name_c = commonjs_wrapper_name;
        eval_source_len = sizeof(dukpy_commonjs_module_wrapper) - 1;
    } else if (strcmp(module_format_c, "module") != 0) {
        JS_ThrowTypeError(ctx, "Invalid module format: %s", module_format_c);
        Py_DECREF(loaded);
        return NULL;
    }

    func_val = JS_Eval(ctx, eval_source_c, eval_source_len, eval_module_name_c,
                       JS_EVAL_TYPE_MODULE | JS_EVAL_FLAG_COMPILE_ONLY);
    if (JS_IsException(func_val)) {
        free(commonjs_wrapper_name);
        Py_DECREF(loaded);
        return NULL;
    }

    if (commonjs_wrapper_name) {
        commonjs_source = JS_NewStringLen(ctx, source_c, (size_t)source_len);
        if (JS_IsException(commonjs_source)) {
            free(commonjs_wrapper_name);
            JS_FreeValue(ctx, func_val);
            Py_DECREF(loaded);
            return NULL;
        }
        if (dukpy_module_set_commonjs_import_meta(ctx, func_val,
                                                  module_id_c, commonjs_source) < 0) {
            free(commonjs_wrapper_name);
            JS_FreeValue(ctx, commonjs_source);
            JS_FreeValue(ctx, func_val);
            Py_DECREF(loaded);
            return NULL;
        }
        JS_FreeValue(ctx, commonjs_source);
    } else if (dukpy_module_set_import_meta(ctx, func_val, module_id_c, 0) < 0) {
        free(commonjs_wrapper_name);
        JS_FreeValue(ctx, func_val);
        Py_DECREF(loaded);
        return NULL;
    }

    module = JS_VALUE_GET_PTR(func_val);
    free(commonjs_wrapper_name);
    JS_FreeValue(ctx, func_val);
    Py_DECREF(loaded);
    return module;
}
