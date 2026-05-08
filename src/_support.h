#ifndef __DUKPY_SUPPORT_H__
#define __DUKPY_SUPPORT_H__

#include "quickjs.h"

/* Rejected promises keep duplicated QuickJS values alive until the eval that
 * created them either observes the rejection or finishes cleanup. */
typedef struct DukPyRejectedPromise {
    JSValue promise;              /* Promise identity used when QuickJS reports it handled. */
    JSValue reason;               /* Rejection value re-thrown as the Python-facing JS error. */
    unsigned long eval_id;        /* Owning eval; prevents stale async failures crossing calls. */
    struct DukPyRejectedPromise *next;
} DukPyRejectedPromise;

/* PyCapsule-owned interpreter state shared by the Python extension entrypoints
 * and QuickJS host callbacks; all fields are private to the C bridge. */
typedef struct DukPyContext {
    JSRuntime *runtime;           /* QuickJS runtime owned and freed with the capsule. */
    JSContext *context;           /* Single QuickJS context reused by JSInterpreter calls. */
    DukPyRejectedPromise *rejected_promises; /* Pending unhandled promise failures. */
    unsigned long current_eval_id;          /* Eval whose async jobs are currently draining. */
    unsigned long next_eval_id;             /* Monotonic non-zero id source for eval calls. */
    unsigned long next_commonjs_wrapper_id; /* Disposable module names for CommonJS retries. */
    int drain_depth;              /* Prevents nested job drains from re-entering QuickJS. */
    int unusable;                 /* Set after pending jobs abort in an uncertain runtime state. */
} DukPyContext;

DukPyContext *get_context_from_capsule(PyObject *pyctx);
PyObject *make_capsule_for_context(DukPyContext *ctx);
int dukpy_should_interrupt(void);
JSValue call_py_function(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv);
char *dukpy_module_normalize(JSContext *ctx, const char *module_base_name,
                             const char *module_name, void *opaque);
JSModuleDef *dukpy_module_loader(JSContext *ctx, const char *module_name, void *opaque);
int dukpy_module_set_import_meta(JSContext *ctx, JSValueConst func_val,
                                 const char *module_name, int is_main);

#endif
