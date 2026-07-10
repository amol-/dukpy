import dep, * as namespace from './dep.js';

globalThis.moduleRuntimePackageLessCommonJsImport = {
  answer: dep.answer,
  defaultIsNamespaceDefault: dep === namespace.default,
  namespaceKeys: Object.keys(namespace).sort(),
  moduleId: dep.moduleId,
  requireId: dep.requireId,
  thisIsExports: dep.thisIsExports,
};
