const answer = dukpy.eval_as_module + dukpy.module;
globalThis.moduleRuntimeEsmSyntax = {
  answer,
  exportedType: typeof answer,
};
export const exportedAnswer = answer;
