#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "quickjs.h"
#include "_support.h"

#ifdef __cplusplus
extern "C" {
#endif

static PyObject *DukPyError;

/* Bound runtime resources without imposing a wall-clock execution limit. */
#define DUKPY_RUNTIME_MEMORY_LIMIT ((size_t)128 * 1024 * 1024)
#define DUKPY_RUNTIME_STACK_SIZE ((size_t)1024 * 1024)
#define DUKPY_RUNTIME_GC_THRESHOLD ((size_t)8 * 1024 * 1024)

/* Shared interrupt predicate for QuickJS execution and Python callback returns. */
int dukpy_should_interrupt(void) {
    return PyErr_CheckSignals() != 0;
}

/* QuickJS runtime callback: non-zero asks QuickJS to abort current execution. */
static int dukpy_interrupt_handler(JSRuntime *rt, void *opaque) {
    (void)rt;
    (void)opaque;
    return dukpy_should_interrupt();
}

/* Promise tracker identity lookup; stored promises are duplicated JSValues. */
static DukPyRejectedPromise *dukpy_find_rejected_promise(DukPyContext *context,
                                                         JSContext *ctx,
                                                         JSValueConst promise) {
    DukPyRejectedPromise *rejection;

    for (rejection = context->rejected_promises; rejection; rejection = rejection->next) {
        if (JS_IsSameValue(ctx, rejection->promise, promise)) {
            return rejection;
        }
    }
    return NULL;
}

/* Drop only rejections created by this eval so previous/outer calls keep ownership. */
static void dukpy_clear_rejected_promises_for_eval(DukPyContext *context, JSContext *ctx,
                                                   unsigned long eval_id) {
    DukPyRejectedPromise **current = &context->rejected_promises;

    while (*current) {
        DukPyRejectedPromise *rejection = *current;

        if (rejection->eval_id == eval_id) {
            *current = rejection->next;
            JS_FreeValue(ctx, rejection->promise);
            JS_FreeValue(ctx, rejection->reason);
            free(rejection);
            continue;
        }
        current = &rejection->next;
    }
}

/* Convert the first unhandled rejection for this eval into the JS exception path. */
static int dukpy_raise_rejected_promise_for_eval(DukPyContext *context, JSContext *ctx,
                                                 JSContext **exception_ctx,
                                                 unsigned long eval_id) {
    DukPyRejectedPromise *rejection;

    for (rejection = context->rejected_promises; rejection; rejection = rejection->next) {
        if (rejection->eval_id == eval_id) {
            JS_Throw(ctx, JS_DupValue(ctx, rejection->reason));
            dukpy_clear_rejected_promises_for_eval(context, ctx, eval_id);
            *exception_ctx = ctx;
            return -1;
        }
    }
    return 0;
}

/* QuickJS host hook that records unhandled promise rejections until job drain. */
static void dukpy_promise_rejection_tracker(JSContext *ctx, JSValueConst promise,
                                            JSValueConst reason, bool is_handled,
                                            void *opaque) {
    DukPyContext *context = (DukPyContext *)opaque;
    DukPyRejectedPromise *rejection;

    if (!context) {
        return;
    }

    rejection = dukpy_find_rejected_promise(context, ctx, promise);
    if (is_handled) {
        DukPyRejectedPromise **current = &context->rejected_promises;

        while (*current) {
            if (*current == rejection) {
                *current = rejection->next;
                JS_FreeValue(ctx, rejection->promise);
                JS_FreeValue(ctx, rejection->reason);
                free(rejection);
                return;
            }
            current = &(*current)->next;
        }
        return;
    }

    if (rejection) {
        return;
    }

    rejection = calloc(1, sizeof(*rejection));
    if (!rejection) {
        return;
    }
    rejection->promise = JS_DupValue(ctx, promise);
    rejection->reason = JS_DupValue(ctx, reason);
    rejection->eval_id = context->current_eval_id;
    rejection->next = context->rejected_promises;
    context->rejected_promises = rejection;
}

/* Microtask boundary: run QuickJS jobs for the current eval and surface failures. */
static int dukpy_drain_pending_jobs(DukPyContext *context, JSContext *ctx,
                                    JSContext **exception_ctx,
                                    unsigned long eval_id) {
    if (context->drain_depth > 0) {
        return dukpy_raise_rejected_promise_for_eval(context, ctx, exception_ctx, eval_id);
    }

    context->drain_depth++;
    while (JS_IsJobPending(context->runtime)) {
        JSContext *job_ctx = NULL;
        int err;

        if (dukpy_should_interrupt()) {
            if (!PyErr_Occurred()) {
                JS_ThrowInternalError(ctx, "interrupted");
            }
            context->unusable = 1;
            context->drain_depth--;
            *exception_ctx = ctx;
            return -1;
        }

        err = JS_ExecutePendingJob(context->runtime, &job_ctx);
        if (err < 0) {
            if (JS_IsJobPending(context->runtime)) {
                context->unusable = 1;
            }
            context->drain_depth--;
            *exception_ctx = job_ctx ? job_ctx : ctx;
            return -1;
        }
    }
    context->drain_depth--;

    return dukpy_raise_rejected_promise_for_eval(context, ctx, exception_ctx, eval_id);
}

/* Restore per-eval state before returning to Python, including nested eval callers. */
static void dukpy_finish_eval(DukPyContext *ctx, unsigned long previous_eval_id) {
    ctx->current_eval_id = previous_eval_id;
    JS_RunGC(ctx->runtime);
    JS_SetGCThreshold(ctx->runtime, DUKPY_RUNTIME_GC_THRESHOLD);
}

/* Allocate formatted error text with PyMem so Python-side cleanup is consistent. */
static char *dukpy_copy_text(const char *text) {
    size_t size = strlen(text) + 1;
    char *copy = PyMem_Malloc(size);

    if (copy) {
        memcpy(copy, text, size);
    }
    return copy;
}

/* JSRuntimeError translation is intentionally narrow: QuickJS owns JavaScript
 * parsing, error text, and frame capture. DukPy carries QuickJS or user-provided
 * stack text unchanged and only joins the first line to an owned stack string. */
static char *dukpy_format_js_exception(const char *exception_message,
                                       const char *stack_message) {
    char *first_line;
    char *message;
    size_t first_line_len;
    size_t stack_len;

    first_line = dukpy_copy_text(exception_message ? exception_message : "JavaScript Error");
    if (!first_line || !stack_message || stack_message[0] == '\0') {
        return first_line;
    }

    first_line_len = strlen(first_line);
    stack_len = strlen(stack_message);
    message = PyMem_Malloc(first_line_len + 1 + stack_len + 1);
    if (!message) {
        PyMem_Free(first_line);
        return NULL;
    }

    memcpy(message, first_line, first_line_len);
    message[first_line_len] = '\n';
    memcpy(message + first_line_len + 1, stack_message, stack_len + 1);
    PyMem_Free(first_line);
    return message;
}

/* Translate a specific JS exception value into DukPyError and consume the JSValue. */
static PyObject *raise_js_exception_value(JSContext *ctx, JSValue exception) {
    JSPropertyDescriptor stack_desc;
    JSAtom stack_atom;
    const char *stack_message = NULL;
    const char *exception_message = NULL;
    char *message;
    int stack_found = 0;
    int stack_message_owned = 0;

    if (PyErr_Occurred()) {
        JS_FreeValue(ctx, exception);
        return NULL;
    }

    if (JS_IsObject(exception) && !JS_IsProxy(exception)) {
        stack_atom = JS_NewAtom(ctx, "stack");
        if (stack_atom == JS_ATOM_NULL) {
            JS_FreeValue(ctx, JS_GetException(ctx));
        } else {
            stack_found = JS_GetOwnProperty(ctx, &stack_desc, exception, stack_atom);
            JS_FreeAtom(ctx, stack_atom);
            if (stack_found < 0) {
                JS_FreeValue(ctx, JS_GetException(ctx));
                stack_found = 0;
            }
            if (stack_found && !(stack_desc.flags & JS_PROP_GETSET) &&
                    JS_IsString(stack_desc.value)) {
                stack_message = JS_ToCString(ctx, stack_desc.value);
                stack_message_owned = stack_message != NULL;
            }
        }
    }

    exception_message = JS_ToCString(ctx, exception);
    message = dukpy_format_js_exception(exception_message, stack_message);
    PyErr_SetString(DukPyError, message ? message : "JavaScript Error");

    if (message) {
        PyMem_Free(message);
    }
    if (stack_message_owned) {
        JS_FreeCString(ctx, stack_message);
    }
    if (exception_message) {
        JS_FreeCString(ctx, exception_message);
    }
    if (stack_found) {
        JS_FreeValue(ctx, stack_desc.value);
        JS_FreeValue(ctx, stack_desc.getter);
        JS_FreeValue(ctx, stack_desc.setter);
    }
    JS_FreeValue(ctx, exception);
    return NULL;
}

/* Fetch QuickJS's pending exception and route it through the Python error boundary. */
static PyObject *raise_js_exception(JSContext *ctx) {
    JSValue exception;

    if (PyErr_Occurred()) {
        exception = JS_GetException(ctx);
        JS_FreeValue(ctx, exception);
        return NULL;
    }

    return raise_js_exception_value(ctx, JS_GetException(ctx));
}

/* Python extension entrypoint: allocate one bounded QuickJS runtime/context pair. */
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

    JS_SetMemoryLimit(ctx->runtime, DUKPY_RUNTIME_MEMORY_LIMIT);
    JS_SetMaxStackSize(ctx->runtime, DUKPY_RUNTIME_STACK_SIZE);
    JS_SetGCThreshold(ctx->runtime, DUKPY_RUNTIME_GC_THRESHOLD);
    JS_SetInterruptHandler(ctx->runtime, dukpy_interrupt_handler, NULL);
    JS_SetHostPromiseRejectionTracker(ctx->runtime, dukpy_promise_rejection_tracker, ctx);
    JS_SetCanBlock(ctx->runtime, false);

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


/* Public host boundary called by dukpy/evaljs.py. Python passes already-adapted
 * source bytes, JSON-encoded globals, and an explicit script/module flag;
 * QuickJS owns JavaScript parsing, module compilation, evaluation, pending-job
 * execution, and result JSON serialization from here downward. The deliberately
 * long body keeps the eval protocol visible behind one deep public boundary. */
static PyObject *DukPy_eval_string(PyObject *self, PyObject *args) {
    PyObject *interpreter;
    PyObject *pyctx = NULL;
    DukPyContext *context = NULL;
    JSContext *ctx = NULL;
    JSContext *exception_ctx = NULL;
    const char *command;
    size_t command_len;
    const char *vars;
    size_t vars_len;
    int eval_as_module = 0;
    const char *module_name = "<dukpy>";
    const char *output = NULL;
    PyObject *result = NULL;
    JSValue eval_result = JS_UNDEFINED;
    JSValue jsvars;
    JSValue json_result = JS_UNDEFINED;
    JSValue global;
    JSValue deferred_exception = JS_UNDEFINED;
    int has_deferred_exception = 0;
    int eval_started = 0;
    unsigned long eval_id = 0;
    unsigned long previous_eval_id = 0;

    if (!PyArg_ParseTuple(args, "Oy#y#|ps", &interpreter, &command, &command_len,
                          &vars, &vars_len, &eval_as_module, &module_name)) {
        return NULL;
    }

    /* Context admission happens before touching QuickJS state; unusable contexts
     * fail closed after aborted pending jobs leave runtime state uncertain. */
    pyctx = PyObject_GetAttrString(interpreter, "_ctx");
    if (!pyctx) {
        PyErr_SetString(DukPyError, "Missing dukpy interpreter context");
        goto finalize;
    }

    context = get_context_from_capsule(pyctx);

    if (!context) {
        PyErr_SetString(DukPyError, "Invalid dukpy interpreter context");
        goto finalize;
    }

    if (context->unusable) {
        PyErr_SetString(DukPyError,
                        "DukPy interpreter context is unusable after aborted pending jobs");
        goto finalize;
    }

    if (context->drain_depth > 0) {
        PyErr_SetString(DukPyError,
                        "Cannot call evaljs while QuickJS Promise jobs are draining");
        goto finalize;
    }

    eval_id = ++context->next_eval_id;
    if (eval_id == 0) {
        eval_id = ++context->next_eval_id;
    }
    previous_eval_id = context->current_eval_id;
    context->current_eval_id = eval_id;

    /* Begin the eval lifetime before host globals or source execution so
     * promise ownership stays local across nested eval calls. */
    ctx = context->context;
    JS_SetContextOpaque(ctx, interpreter);
    JS_UpdateStackTop(context->runtime);
    JS_RunGC(context->runtime);
    eval_started = 1;

    /* Publish Python-provided globals and host callbacks in the QuickJS global
     * object before compilation; QuickJS still owns all JavaScript semantics. */
    jsvars = JS_ParseJSON(ctx, vars, vars_len, "<dukpy>");
    if (JS_IsException(jsvars)) {
        exception_ctx = ctx;
        goto finalize;
    }

    global = JS_GetGlobalObject(ctx);
    JS_SetPropertyStr(ctx, global, "dukpy", jsvars);
    JS_SetPropertyStr(ctx, global, "call_python",
                      JS_NewCFunction(ctx, call_py_function, "call_python", 1));
    JS_FreeValue(ctx, global);

    /* Source execution is either the native module pipeline or a global script;
     * the caller's explicit mode is the only classification DukPy performs. */
    if (eval_as_module) {
        JSValue func_val = JS_Eval(ctx, command, command_len, module_name,
                                   JS_EVAL_TYPE_MODULE | JS_EVAL_FLAG_COMPILE_ONLY);
        if (JS_IsException(func_val)) {
            exception_ctx = ctx;
            goto finalize;
        }

        if (JS_ResolveModule(ctx, func_val) < 0) {
            JS_FreeValue(ctx, func_val);
            exception_ctx = ctx;
            goto finalize;
        }

        if (dukpy_module_set_import_meta(ctx, func_val, module_name, 1) < 0) {
            JS_FreeValue(ctx, func_val);
            exception_ctx = ctx;
            goto finalize;
        }

        eval_result = JS_EvalFunction(ctx, func_val);
    } else {
        eval_result = JS_Eval(ctx, command, command_len, "<dukpy>", JS_EVAL_TYPE_GLOBAL);
    }
    if (JS_IsException(eval_result)) {
        eval_result = JS_UNDEFINED;
        dukpy_clear_rejected_promises_for_eval(context, ctx, eval_id);
        exception_ctx = ctx;
        goto finalize;
    }

    /* Drain microtasks once source execution settles so promises can affect the
     * returned value or surface as this eval's Python-facing exception. */
    exception_ctx = ctx;
    if (dukpy_drain_pending_jobs(context, ctx, &exception_ctx, eval_id) < 0) {
        dukpy_clear_rejected_promises_for_eval(context, ctx, eval_id);
        goto finalize;
    }
    exception_ctx = NULL;

    if (JS_IsUndefined(eval_result)) {
        Py_INCREF(Py_None);
        result = Py_None;
        goto finalize;
    }

    /* JSON serialization is part of the eval boundary: toJSON may enqueue more
     * jobs, and serialization failures must win over cleanup-only rejections. */
    json_result = JS_JSONStringify(ctx, eval_result, JS_UNDEFINED, JS_UNDEFINED);
    JS_FreeValue(ctx, eval_result);
    eval_result = JS_UNDEFINED;
    if (JS_IsException(json_result)) {
        JSContext *ignored_exception_ctx = ctx;

        json_result = JS_UNDEFINED;
        deferred_exception = JS_GetException(ctx);
        has_deferred_exception = 1;
        if (dukpy_drain_pending_jobs(context, ctx, &ignored_exception_ctx, eval_id) < 0) {
            JSValue ignored_exception = JS_GetException(ignored_exception_ctx);
            JS_FreeValue(ignored_exception_ctx, ignored_exception);
        }
        dukpy_clear_rejected_promises_for_eval(context, ctx, eval_id);
        goto finalize;
    }

    exception_ctx = ctx;
    if (dukpy_drain_pending_jobs(context, ctx, &exception_ctx, eval_id) < 0) {
        dukpy_clear_rejected_promises_for_eval(context, ctx, eval_id);
        goto finalize;
    }
    exception_ctx = NULL;

    if (JS_IsUndefined(json_result)) {
        PyErr_SetString(DukPyError, "Invalid Result Value");
        goto finalize;
    }

    /* Convert the serialized JSON bytes for Python; ownership returns to
     * QuickJS in the shared cleanup path below. */
    output = JS_ToCString(ctx, json_result);
    JS_FreeValue(ctx, json_result);
    json_result = JS_UNDEFINED;
    if (output == NULL) {
        PyErr_SetString(DukPyError, "Invalid Result Value");
        goto finalize;
    }

    result = Py_BuildValue("y", output);

finalize:
    /* The single cleanup exit releases QuickJS values before restoring eval
     * state, while preserving a deferred JS exception for Python translation. */
    if (ctx) {
        if (output) {
            JS_FreeCString(ctx, output);
        }
        JS_FreeValue(ctx, json_result);
        JS_FreeValue(ctx, eval_result);
    }
    if (has_deferred_exception) {
        result = raise_js_exception_value(ctx, deferred_exception);
        has_deferred_exception = 0;
    } else if (exception_ctx) {
        result = raise_js_exception(exception_ctx);
        exception_ctx = NULL;
    }

    if (eval_started) {
        dukpy_finish_eval(context, previous_eval_id);
    }
    Py_XDECREF(pyctx);

    return result;
}


static PyMethodDef DukPy_methods[] = {
    {"eval_string", DukPy_eval_string, METH_VARARGS,
     "Evaluate adapted JavaScript source through QuickJS."},
    {"create_context", DukPy_create_context, METH_NOARGS, "Create an interpreter context where to run code"},
    {NULL, NULL, 0, NULL}
};

static char DukPy_doc[] = "Provides Javascript support to Python through the QuickJS library.";


static struct PyModuleDef dukpymodule = {
    PyModuleDef_HEAD_INIT,
    "_dukpy",
    DukPy_doc,
    -1,
    DukPy_methods
};

/* Python extension initialization: expose the native methods and JSRuntimeError. */
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

#ifdef __cplusplus
}
#endif
