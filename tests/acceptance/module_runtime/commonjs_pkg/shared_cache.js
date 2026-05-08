globalThis.moduleRuntimeCommonJsLoads = (globalThis.moduleRuntimeCommonJsLoads || 0) + 1;
module.exports = {loadCount: globalThis.moduleRuntimeCommonJsLoads};
