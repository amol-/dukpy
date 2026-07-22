# Changes in 0.6.0

## New features and capabilities

- JavaScript engine migrated from Duktape to QuickJS-NG v0.11.0, with modern
  JavaScript syntax and native Promise/job-queue support.
- Added `dukpy.run(path, **kwargs)` and `JSInterpreter.run(path, **kwargs)`;
  the `dukpy` CLI uses this file runner. `run()` supports native ESM static
  `import`/`export`, `import.meta.url`, `import.meta.main`, and top-level
  `await`.
- File entrypoints use Node-like classification: `.mjs` is ESM, `.cjs` is
  CommonJS, and `.js` follows the nearest `package.json` `"type"` of `module`
  or `commonjs`. Package-less ambiguous `.js` files are probed by compiling the
  CommonJS wrapper first, then native ESM; source text is not scanned.
- The QuickJS CommonJS runtime supports `require`, `module`, `exports`,
  `__filename`, and `__dirname`. Its cache is shared with ESM/CommonJS interop,
  and failed modules are removed so they can be retried.
- ESM can import CommonJS: the default export is `module.exports`; the only
  named exports are `module`, `exports`, and `require`. Named exports are not
  inferred from CommonJS source.
- Node-like `fs`, `path`, `url`, `querystring`, and `punycode` shims remain
  available.
- Promise microtasks drain before result serialization; Promise failures during
  evaluation or serialization raise `JSRuntimeError`.
- Python callbacks preserve argument order and JSON types, support Unicode names
  and Unicode/emoji values, map `None` returns to JavaScript `undefined`, and
  turn missing callbacks and Python exceptions into catchable `ReferenceError`
  and `InternalError`, respectively.
- Result conversion more closely follows `JSON.stringify`: `null`, `undefined`,
  `NaN`, `Infinity`, and `-Infinity` map to Python `None`; circular references
  and BigInt conversion failures raise runtime errors.
- Stack exhaustion and oversized allocations raise runtime errors, Python signal
  exceptions propagate, and blocking `Atomics.wait` is disabled.
- The npm installer uses HTTPS for registry and tarball URLs; rejects unsafe tar
  paths, path traversal, multiple roots, unsupported entries, and symlink
  destination escapes; and reports missing metadata, versions, and tarball URLs
  more clearly.
- Bundled TypeScript was upgraded to 5.7.3.

## No longer available and behavior changes

- Generic Babel support was removed: `dukpy.babel_compile`, `dukpy.webassets.BabelJS`, and the `babeljs` WebAssets filter are unavailable; bundled Babel remains only for JSX transpilation.
- CoffeeScript support, including `dukpy.coffee_compile`, was removed.
- Duktape and its `Duktape` global, `Duktape.modSearch`, module system, error
  wording, and stack formatting are gone; code relying on them must use DukPy's
  QuickJS/CommonJS behavior and update exact-message expectations.
- Python versions below 3.9 are unsupported; 0.6.0 requires Python `>=3.9`,
  and old Python 2 compatibility code is gone.
- The old `dukpy/run.py` module is removed. Use `dukpy.run(...)`; code importing
  `main` from `dukpy.run` breaks. The `dukpy` console command remains and now
  targets `dukpy.cli:main`.
- `evaljs()` remains script-only and does not auto-detect ESM syntax; run static
  `import`/`export` through `dukpy.run()` file entrypoints.
- CommonJS module IDs now use canonical file-like IDs with extensions and
  forward slashes, so exact old `module.id` or `require.id` strings may differ.
- `require('x.mjs')` and `require()` of `.js` files classified as ESM fail; use
  ESM `import`/`dukpy.run()`. CommonJS named imports are unsupported unless they
  are `module`, `exports`, or `require`; use the default import for its API.
- Top-level functions and Symbols now raise `Invalid Result Value`; `undefined`,
  `NaN`, and infinities map to `None`, and Duktape-specific or formerly `{}`
  results may differ.
- The installer rejects HTTP registry or tarball URLs, tarballs with symlinks,
  path traversal, multiple roots, or unsupported entries, and symlinked
  destinations.
