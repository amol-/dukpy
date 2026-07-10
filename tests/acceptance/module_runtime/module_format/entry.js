import {value as explicitModuleValue, url as explicitModuleUrl} from './explicit.mjs';
import explicitCommonJs from './explicit.cjs';
import {value as packageModuleValue, url as packageModuleUrl} from './module_package';
import packageCommonJs from './commonjs_package';
import packageModuleExplicitCommonJs from './module_package/explicit.cjs';
import {value as packageCommonJsExplicitModule} from './commonjs_package/explicit.mjs';

globalThis.moduleRuntimeModuleFormats = {
  explicitModuleValue,
  explicitModuleUrl,
  explicitCommonJs,
  packageModuleValue,
  packageModuleUrl,
  packageCommonJs,
  packageModuleExplicitCommonJs,
  packageCommonJsExplicitModule,
};
