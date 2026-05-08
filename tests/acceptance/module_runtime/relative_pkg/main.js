import {value, meta} from './dep.js';

globalThis.moduleRuntimeImportMetaAndRelative = {
  answer: value + 1,
  mainUrl: import.meta.url,
  mainIsMain: import.meta.main,
  depUrl: meta.url,
  depIsMain: meta.main,
};
