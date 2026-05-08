import {value, url} from './slashless_dep.js';

globalThis.moduleRuntimeSlashlessRelativeImport = {
  value,
  url,
  mainUrl: import.meta.url,
};
