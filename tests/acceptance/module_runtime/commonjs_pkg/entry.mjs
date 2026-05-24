import cjs, { module, exports, require } from './main.js';
import * as cjsNamespace from './main.js';

globalThis.moduleRuntimeCommonJsImport = cjs;
globalThis.moduleRuntimeCommonJsInteropContract = {
    defaultIsModuleExports: cjs === cjsNamespace.default &&
        cjs === module.exports && cjs === exports,
    inferredAnswerExportPresent: Object.prototype.hasOwnProperty.call(cjsNamespace, 'answer'),
    namespaceKeys: Object.keys(cjsNamespace).sort(),
    requireId: require.id,
};
