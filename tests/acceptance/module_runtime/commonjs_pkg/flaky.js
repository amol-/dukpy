globalThis.moduleRuntimeCommonJsFlakyAttempts = (globalThis.moduleRuntimeCommonJsFlakyAttempts || 0) + 1;
if (!globalThis.moduleRuntimeCommonJsFlakyShouldPass) {
  throw new Error('flaky cjs failed');
}
module.exports = {attempts: globalThis.moduleRuntimeCommonJsFlakyAttempts};
