import cjs from './shared_cache.js';

globalThis.moduleRuntimeCommonJsSharedCache = {
  importedLoadCount: cjs.loadCount,
  globalLoadCount: globalThis.moduleRuntimeCommonJsLoads,
};
