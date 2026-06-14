# Changes in 0.6.0

## New features and capabilities

- JavaScript engine migrated from Duktape to QuickJS-NG v0.11.0.
  - Better modern JavaScript syntax support.
  - Native Promise/job-queue support.

- New public file runner API:
  - `dukpy.run(path, **kwargs)`
  - `JSInterpreter.run(path, **kwargs)`
  - The `dukpy` CLI now uses this path-based runner.

- Native ES module support for file entrypoints.
  - `.mjs` runs as native ESM.
  - `.cjs` runs as CommonJS.
  - `.js` follows nearest `package.json` `"type": "module"` / `"commonjs"`.
  - Package-less ambiguous `.js` files are probed instead of source-scanned.

- ESM features now supported through `run()`:
  - static `import`
  - `export`
  - `import.meta.url`
  - `import.meta.main`
  - top-level `await`

- CommonJS runtime rewritten for QuickJS.
  - Supports `require`, `module`, `exports`.
  - Supports `__filename` and `__dirname`.
  - Has a module cache shared between global `require()` and ESM/CommonJS interop.
  - Failed CommonJS modules are removed from cache so they can be retried.

- ESM importing CommonJS is supported.
  - Default import maps to `module.exports`.
  - Namespace exposes: `default`, `module`, `exports`, `require`.
  - No named-export inference from CommonJS source.

- Node-like compatibility shims still shipped and tested:
  - `fs`
  - `path`
  - `url`
  - `querystring`
  - `punycode`

- Promise/microtask behavior is now handled.
  - Promise microtasks are drained before result serialization.
  - Promise failures during evaluation/serialization propagate as `JSRuntimeError`.

- Improved Python callback bridge.
  - Preserves argument order and JSON types.
  - Supports Unicode function names and Unicode/emoji values.
  - Python `None` callback returns become JavaScript `undefined`.
  - Missing Python callbacks become catchable JS `ReferenceError`.
  - Python exceptions become catchable JS `InternalError`.

- Result conversion now follows `JSON.stringify` more closely.
  - `null`, `undefined`, `NaN`, `Infinity`, `-Infinity` map to Python `None`.
  - JSON conversion failures like circular references and BigInt produce runtime errors.

- Improved runtime safety.
  - Stack exhaustion and oversized allocations are reported as runtime errors.
  - Python signal exceptions propagate.
  - Blocking `Atomics.wait` is disabled.

- Installer hardening.
  - npm registry access now uses HTTPS.
  - Tarball URLs must be HTTPS.
  - Rejects unsafe tar paths, path traversal, multiple archive roots, unsupported tar entries, and symlink destination escapes.
  - Better errors for missing metadata, missing versions, missing tarball URLs.

- Packaging modernization.
  - Moved project metadata to `pyproject.toml`.
  - Declares `requires-python = ">=3.9"`.
  - Adds Ruff/pre-commit lint setup.
  - Builds sdist with `python -m build`.

## No longer available and behavior changes

- Duktape-specific behavior is gone.
  - No Duktape engine.
  - Code relying on the JS global `Duktape` or `Duktape.modSearch` will break.
  - Module loading is now DukPy’s QuickJS/CommonJS shim instead of Duktape’s module system.

- Python versions below 3.9 are no longer supported.
  - 0.6.0 declares Python `>=3.9`.
  - Old Python 2 compatibility code is gone.

- `dukpy.run` changed shape.
  - Old `dukpy/run.py` module was removed.
  - New public API is `dukpy.run(...)` function.
  - Code like `from dukpy.run import main` will break.
  - The console command `dukpy` still exists, but now points to `dukpy.cli:main`.

- `evaljs()` remains script-only.
  - It does not auto-detect ESM syntax.
  - Static `import` / `export` should be run via `dukpy.run()` file entrypoints, not raw `evaljs()` source text.

- CommonJS module IDs may differ.
  - New loader uses canonical file-like module IDs with extensions and forward slashes.
  - Code depending on old Duktape/loader `module.id` or `require.id` exact strings may see changed values.

- `require()` no longer runs ES modules as CommonJS.
  - `require('x.mjs')` errors.
  - `require()` of `.js` files classified as ESM errors.
  - This is intentional; use ESM `import` / `dukpy.run()` for modules.

- CommonJS named exports are not inferred.
  - `import { name } from './commonjs.js'` is not supported unless the synthetic namespace has that name.
  - Use default import for CommonJS exports.

- JavaScript error messages/stacks changed.
  - Errors now use QuickJS wording and stack formatting, not Duktape wording.
  - Tests expecting exact old Duktape messages will need updates.

- Result serialization changed for some edge values.
  - Top-level functions/Symbols now raise `Invalid Result Value`.
  - `undefined`, `NaN`, and infinities now map to `None`.
  - Some values that previously looked like `{}` or Duktape-specific output may differ.

- Installer is stricter.
  - HTTP registry/tarball URLs are rejected.
  - Tarballs with symlinks, path traversal, multiple roots, or unsupported entries are rejected.
  - Installing through symlinked destinations is rejected.
