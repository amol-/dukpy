import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

import dukpy


ACCEPTANCE_DIR = Path(__file__).parent


# Native ESM, import.meta, and top-level await


def test_native_esm_syntax_program_runs_and_updates_interpreter_state():
    assert (
        dukpy.evaljs_module(
            _read_case("esm_syntax.js"),
            module_name="esm_syntax.js",
            eval_as_module=40,
            module=2,
        )
        == {}
    )

    interpreter = dukpy.JSInterpreter()

    assert (
        interpreter.evaljs_module(
            _read_case("esm_syntax.js"),
            module_name="esm_syntax.js",
            eval_as_module=40,
            module=2,
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeEsmSyntax") == {
        "answer": 42,
        "exportedType": "number",
    }


def test_import_meta_and_relative_import_program_reports_module_urls():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert (
        interpreter.evaljs_module(
            _read_case("relative_pkg/main.js"),
            module_name="relative_pkg/main.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeImportMetaAndRelative") == {
        "answer": 42,
        "mainUrl": "relative_pkg/main.js",
        "mainIsMain": True,
        "depUrl": "relative_pkg/dep.js",
        "depIsMain": False,
    }


def test_slashless_module_name_program_resolves_relative_imports_from_root():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert (
        interpreter.evaljs_module(
            _read_case("slashless_relative_import.js"),
            module_name="slashless_relative_import.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeSlashlessRelativeImport") == {
        "value": 42,
        "url": "slashless_dep.js",
        "mainUrl": "slashless_relative_import.js",
    }


def test_import_meta_only_dependency_program_runs_as_a_module():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert (
        interpreter.evaljs_module(
            _read_case("import_meta_only_entry.js"),
            module_name="import_meta_only_entry.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeImportMetaOnly") == (
        "import_meta_only_dep.js"
    )


def test_top_level_await_dependency_program_runs_as_a_module():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert (
        interpreter.evaljs_module(
            _read_case("top_level_await_entry.js"),
            module_name="top_level_await_entry.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeTopLevelAwaitBlock") == 42


# Package format resolution


def test_module_format_program_uses_extensions_and_package_type_metadata():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert (
        interpreter.evaljs_module(
            _read_case("module_format/entry.js"),
            module_name="module_format/entry.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeModuleFormats") == {
        "explicitModuleValue": 10,
        "explicitModuleUrl": "module_format/explicit.mjs",
        "explicitCommonJs": {
            "value": 20,
            "moduleId": "module_format/explicit.cjs",
            "requireId": "module_format/explicit.cjs",
            "thisIsExports": True,
        },
        "packageModuleValue": 30,
        "packageModuleUrl": "module_format/module_package/main.js",
        "packageCommonJs": {
            "value": 40,
            "moduleId": "module_format/commonjs_package/main.js",
            "requireId": "module_format/commonjs_package/main.js",
            "thisIsExports": True,
            "syntaxLookingText": (
                "import value from './missing.js'; export default value; await value;"
            ),
        },
        "packageModuleExplicitCommonJs": {
            "value": 31,
            "moduleId": "module_format/module_package/explicit.cjs",
            "requireId": "module_format/module_package/explicit.cjs",
        },
        "packageCommonJsExplicitModule": 41,
    }

    require_interpreter = dukpy.JSInterpreter()
    require_interpreter.loader.register_path(str(ACCEPTANCE_DIR))
    assert require_interpreter.evaljs(
        "({"
        "explicit: require('module_format/explicit.cjs').value, "
        "packageMain: require('module_format/commonjs_package').moduleId"
        "})"
    ) == {
        "explicit": 20,
        "packageMain": "module_format/commonjs_package/main.js",
    }


def test_module_format_extensionless_names_do_not_probe_mjs_or_cjs():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    with pytest.raises(dukpy.JSRuntimeError) as import_exc:
        interpreter.evaljs_module(
            "import './module_format/extensionless_esm_only';",
            module_name="module_format_extensionless_entry.mjs",
        )
    assert "cannot find module: module_format/extensionless_esm_only" in str(
        import_exc.value
    )

    with pytest.raises(dukpy.JSRuntimeError) as require_exc:
        interpreter.evaljs("require('module_format/extensionless_cjs_only')")
    assert "cannot find module: module_format/extensionless_cjs_only" in str(
        require_exc.value
    )


# CommonJS interop


def test_commonjs_import_program_exposes_default_export_object():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert (
        interpreter.evaljs_module(
            _read_case("commonjs_pkg/entry.js"),
            module_name="commonjs_pkg/entry.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsImport") == {
        "answer": 42,
        "keywordNames": {"export": 1, "import": 2},
        "keywordPropertyAccess": 7,
        "asyncArrowType": "function",
        "moduleId": "commonjs_pkg/main.js",
        "requireId": "commonjs_pkg/main.js",
        "thisIsExports": True,
    }
    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsInteropContract") == {
        "defaultIsModuleExports": True,
        "inferredAnswerExportPresent": False,
        "namespaceKeys": ["default", "exports", "module", "require"],
        "requireId": "commonjs_pkg/main.js",
    }


def test_commonjs_module_ids_are_not_rewritten():
    import_id = 'pkg/import-"quoted"\\control\x01line\u2028paragraph\u2029.js'
    require_id = 'pkg/require-"quoted"\\control\x01line\u2028paragraph\u2029.js'
    source = "exports.summary = { moduleId: module.id, requireId: require.id };"
    loader = MagicMock()
    loader.lookup.side_effect = lambda module_name: (
        (module_name, None) if module_name in {import_id, require_id} else (None, None)
    )
    loader.load.side_effect = lambda module_name: (
        (module_name, source, "commonjs")
        if module_name in {import_id, require_id}
        else (None, None, None)
    )
    interpreter = dukpy.JSInterpreter()
    _use_loader(interpreter, loader)

    assert (
        interpreter.evaljs_module(
            "import cjs from "
            + json.dumps(import_id)
            + "; globalThis.moduleRuntimeCommonJsModuleIdImport = cjs.summary;",
            module_name="commonjs_module_id_entry.mjs",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsModuleIdImport") == {
        "moduleId": import_id,
        "requireId": import_id,
    }
    assert interpreter.evaljs("require(" + json.dumps(require_id) + ").summary") == {
        "moduleId": require_id,
        "requireId": require_id,
    }


def test_commonjs_source_is_not_inspected_by_dukpy():
    module_id = "pkg/syntax-looking-commonjs.js"
    source = (
        "var syntaxText = \"import maybe from 'not-real'; export default 1; await value;\";\n"
        '/* import ignored from "comment"; export const ignored = 1; */\n'
        "// import ignoredLine from 'comment'; export default ignoredLine;\n"
        "exports.summary = { syntaxText: syntaxText, reachedRuntime: true };\n"
    )
    loader = MagicMock()
    loader.lookup.side_effect = lambda module_name: (
        (module_name, None) if module_name == module_id else (None, None)
    )
    loader.load.side_effect = lambda module_name: (
        (module_name, source, "commonjs")
        if module_name == module_id
        else (None, None, None)
    )
    interpreter = dukpy.JSInterpreter()
    _use_loader(interpreter, loader)

    assert interpreter.evaljs("require(" + json.dumps(module_id) + ").summary") == {
        "syntaxText": "import maybe from 'not-real'; export default 1; await value;",
        "reachedRuntime": True,
    }


def test_esm_import_and_global_require_escape_commonjs_source_the_same_way():
    import_id = "pkg/import-escaped-source.js"
    require_id = "pkg/require-escaped-source.js"
    large_text = "x" * 70000
    source = (
        'var escaped = "quote: \\" backslash: \\\\ control: \x02 line: \u2028 paragraph: \u2029";\n'
        f'var large = "{large_text}";\n'
        "exports.summary = {\n"
        "  quotePresent: escaped.indexOf('\"') !== -1,\n"
        "  backslashPresent: escaped.indexOf('backslash: \\\\') !== -1,\n"
        "  controlCode: escaped.charCodeAt(escaped.indexOf('control: ') + 9),\n"
        "  lineSeparatorPresent: escaped.indexOf('\u2028') !== -1,\n"
        "  paragraphSeparatorPresent: escaped.indexOf('\u2029') !== -1,\n"
        "  largeLength: large.length\n"
        "};\n"
    )
    loader = MagicMock()
    loader.lookup.side_effect = lambda module_name: (
        (module_name, None) if module_name in {import_id, require_id} else (None, None)
    )
    loader.load.side_effect = lambda module_name: (
        (module_name, source, "commonjs")
        if module_name in {import_id, require_id}
        else (None, None, None)
    )
    interpreter = dukpy.JSInterpreter()
    _use_loader(interpreter, loader)

    assert (
        interpreter.evaljs_module(
            "import cjs from "
            + json.dumps(import_id)
            + "; globalThis.moduleRuntimeCommonJsEscapedImport = cjs.summary;",
            module_name="commonjs_escaped_import_entry.mjs",
        )
        == {}
    )

    expected = {
        "quotePresent": True,
        "backslashPresent": True,
        "controlCode": 2,
        "lineSeparatorPresent": True,
        "paragraphSeparatorPresent": True,
        "largeLength": len(large_text),
    }
    assert (
        interpreter.evaljs("globalThis.moduleRuntimeCommonJsEscapedImport") == expected
    )
    assert (
        interpreter.evaljs("require(" + json.dumps(require_id) + ").summary")
        == expected
    )


def test_commonjs_import_program_does_not_infer_named_exports_from_source():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs_module(
            _read_case("commonjs_pkg/named_export_entry.js"),
            module_name="commonjs_pkg/named_export_entry.js",
        )

    assert "answer" in str(exc.value)


# Cache and retry behavior


def test_commonjs_compile_time_syntax_errors_do_not_poison_retries():
    require_id = "syntax-retry-require"
    import_id = "syntax-retry-import"
    bad_source = "exports.value = ;"
    good_source = "exports.value = module.id + ':' + require.id;"
    load_attempts = {require_id: 0, import_id: 0}

    def load_module(module_name):
        if module_name not in load_attempts:
            return None, None, None
        load_attempts[module_name] += 1
        source = bad_source if load_attempts[module_name] == 1 else good_source
        return module_name, source, "commonjs"

    loader = MagicMock()
    loader.lookup.side_effect = lambda module_name: (
        (module_name, None) if module_name in load_attempts else (None, None)
    )
    loader.load.side_effect = load_module
    interpreter = dukpy.JSInterpreter()
    _use_loader(interpreter, loader)

    with pytest.raises(dukpy.JSRuntimeError) as require_exc:
        interpreter.evaljs("require(" + json.dumps(require_id) + ")")
    assert "SyntaxError" in str(require_exc.value)
    assert interpreter.evaljs("require(" + json.dumps(require_id) + ").value") == (
        require_id + ":" + require_id
    )

    with pytest.raises(dukpy.JSRuntimeError) as import_exc:
        interpreter.evaljs_module(
            "import cjs from "
            + json.dumps(import_id)
            + "; globalThis.moduleRuntimeCommonJsSyntaxRetry = cjs.value;",
            module_name="commonjs_syntax_retry_entry.mjs",
        )
    assert "SyntaxError" in str(import_exc.value)
    assert (
        interpreter.evaljs_module(
            "import cjs from "
            + json.dumps(import_id)
            + "; globalThis.moduleRuntimeCommonJsSyntaxRetry = cjs.value;",
            module_name="commonjs_syntax_retry_entry.mjs",
        )
        == {}
    )
    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsSyntaxRetry") == (
        import_id + ":" + import_id
    )
    assert load_attempts == {require_id: 2, import_id: 2}


def test_global_require_and_esm_commonjs_interop_share_module_cache():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    assert interpreter.evaljs(
        "var shared = require('commonjs_pkg/shared_cache'); "
        "shared.loadCount = 42; shared;"
    ) == {"loadCount": 42}
    assert (
        interpreter.evaljs_module(
            _read_case("commonjs_pkg/shared_cache_entry.js"),
            module_name="commonjs_pkg/shared_cache_entry.js",
        )
        == {}
    )

    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsSharedCache") == {
        "importedLoadCount": 42,
        "globalLoadCount": 1,
    }


def test_failed_commonjs_require_is_removed_from_runtime_cache():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs("require('commonjs_pkg/flaky')")

    assert "Error: flaky cjs failed" in str(exc.value)
    assert interpreter.evaljs(
        "globalThis.moduleRuntimeCommonJsFlakyShouldPass = true; "
        "require('commonjs_pkg/flaky');"
    ) == {"attempts": 2}


def test_failed_esm_commonjs_import_can_be_retried_with_same_module_name():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))
    code = _read_case("commonjs_pkg/flaky_entry.js")

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs_module(code, module_name="commonjs_pkg/flaky_entry.js")

    assert "Error: flaky cjs failed" in str(exc.value)
    assert (
        interpreter.evaljs(
            "globalThis.moduleRuntimeCommonJsFlakyShouldPass = true; "
            "globalThis.moduleRuntimeCommonJsFlakyAttempts || 0;"
        )
        == 1
    )
    assert (
        interpreter.evaljs_module(code, module_name="commonjs_pkg/flaky_entry.js") == {}
    )
    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsFlakyAttempts") == 2
    assert (
        interpreter.evaljs_module(code, module_name="commonjs_pkg/flaky_entry.js") == {}
    )
    assert interpreter.evaljs("globalThis.moduleRuntimeCommonJsFlakyAttempts") == 2


# Missing-module and error reporting


def test_missing_esm_import_program_reports_missing_module_name():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs_module(
            _read_case("error_pkg/missing_esm_import.js"),
            module_name="error_pkg/missing_esm_import.js",
        )

    assert "cannot find module: error_pkg/missing.js" in str(exc.value)


def test_missing_commonjs_require_program_reports_missing_module_name():
    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(ACCEPTANCE_DIR))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs(_read_case("missing_commonjs_require.js"))

    assert "cannot find module: missing_module" in str(exc.value)


def _use_loader(interpreter, loader):
    interpreter._loader = loader
    interpreter.export_function("dukpy.load_module", loader.load)


def _read_case(name):
    return (ACCEPTANCE_DIR / name).read_text(encoding="utf-8")
