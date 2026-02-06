#ifndef __DUKPY_SUPPORT_H__
#define __DUKPY_SUPPORT_H__

#include "quickjs.h"

typedef struct DukPyContext {
    JSRuntime *runtime;
    JSContext *context;
} DukPyContext;

DukPyContext *get_context_from_capsule(PyObject *pyctx);
PyObject *make_capsule_for_context(DukPyContext *ctx);
JSValue call_py_function(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv);
JSValue require_set_module_id(JSContext *ctx, JSValueConst this_val, int argc, JSValueConst *argv);
char *dukpy_module_normalize(JSContext *ctx, const char *module_base_name,
                             const char *module_name, void *opaque);
JSModuleDef *dukpy_module_loader(JSContext *ctx, const char *module_name, void *opaque);
int dukpy_module_set_import_meta(JSContext *ctx, JSValueConst func_val,
                                 const char *module_name, int is_main);

#endif
