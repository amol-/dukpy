# Contributing

## Guidelines

### QuickJS owns JavaScript parsing

DukPy wraps QuickJS to provide JavaScript support in Python. It must stay as close
as possible to Node.js semantics for the JavaScript surface, within what QuickJS
itself allows.

Do **not** implement JavaScript parsing, lexing, or semantic detection in DukPy
code. In particular:

- Do not inspect JavaScript source character-by-character to infer syntax.
- Do not classify JavaScript as modules/scripts/CommonJS by scanning strings.
- Do not detect `import`, `export`, `await`, comments, strings, templates, or
  identifiers with handwritten C or Python logic.
- Do not rewrite JavaScript source based on DukPy's own understanding of the
  language grammar.

QuickJS is the JavaScript parser and evaluator. If we need to know whether
JavaScript is valid, whether it is a module, or how syntax should behave, route
that decision through QuickJS or through explicit user/API intent. DukPy may adapt
host integration around QuickJS, but it must not become a partial JavaScript
interpreter.

Compatibility shims, module loading, and CommonJS support must be designed around
clear boundaries: explicit modes, QuickJS parsing/evaluation, and runtime-level
JavaScript behavior. Any change that appears to require parsing JavaScript text in
DukPy should be treated as a design problem and discussed before implementation.

### Acceptance-test driven development

Major features and capabilities should be driven by acceptance tests.

Use `tests/acceptance/` for these tests. Each major feature gets its own
subdirectory containing:

- a dedicated JavaScript test case that demonstrates the expected user-facing
  behavior;
- a Python test that loads and runs that JavaScript case through DukPy.

Prefer small, concrete JavaScript programs over prose specifications. The
JavaScript case should read like the behavior a user expects, while the Python
wrapper should stay thin and focused on running the case and asserting the
result.

Task tracking for architectural work should use probe-driven development: keep
small, explicit evolutions close to the code under change, validate each
capability with an acceptance case, and avoid separate BDD feature tracking.

### Code design style

Keep code simple, production-ready, and easy for a human to review.

- Prefer small, isolated changes with no effects at a distance.
- Prefer well-encapsulated deep modules over scattered behavior.
- Keep one capability understandable through one clear boundary whenever possible.
- Avoid unnecessary indirection, tiny single-use helpers, and temporary variables
  that are used once.
- Keep functions concise when that improves clarity, but do not split code just
  to satisfy style rules.
- Comments should explain what and why; code should explain how.
- Implement real behavior, not shortcuts that only satisfy current tests.
- Tests should validate meaningful user-facing behavior, not incidental details.
- Prefer standard-library solutions and existing project patterns before adding
  abstractions or dependencies.
