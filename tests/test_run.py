# -*- coding: utf-8 -*-
import json
import logging
import ntpath
import sys

import pytest

import dukpy
import dukpy.cli
import dukpy.module_loader


def run_cli_script(monkeypatch, tmp_path, source):
    script = tmp_path / "script.js"
    script.write_text(source, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dukpy", str(script)])
    return dukpy.cli.main()


def test_run_main_executes_plain_script_through_node_like_interpreter(
    monkeypatch, tmp_path, caplog
):
    caplog.set_level(logging.INFO, logger="dukpy.interpreter")

    run_cli_script(monkeypatch, tmp_path, "console.log('plain script');\n")

    assert "plain script" in caplog.messages


def test_run_main_adapts_leading_shebang_without_scanning_javascript(
    monkeypatch, tmp_path, caplog
):
    caplog.set_level(logging.INFO, logger="dukpy.interpreter")

    run_cli_script(
        monkeypatch,
        tmp_path,
        "#!/usr/bin/env dukpy\nconsole.log('hello ☃');\n",
    )

    assert "hello ☃" in caplog.messages


def test_run_main_shebang_adaptation_preserves_syntax_error_line_numbers(
    monkeypatch, tmp_path
):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        run_cli_script(
            monkeypatch,
            tmp_path,
            "#!/usr/bin/env dukpy\nvar ok = 1;\nvar = ;\n",
        )

    assert "script.js:3" in str(exc.value)


def test_top_level_run_executes_js_as_commonjs_by_default(tmp_path):
    entry = tmp_path / "entry.js"
    dep = tmp_path / "dep.js"
    entry.write_text(
        "var dep = require('./dep');\n"
        "module.exports = {\n"
        "  value: dep.value + dukpy.offset,\n"
        "  filename: __filename,\n"
        "  dirname: __dirname,\n"
        "  firstWrapperArgumentIsExports: arguments[0] === exports\n"
        "};\n",
        encoding="utf-8",
    )
    dep.write_text("exports.value = 40;\n", encoding="utf-8")

    assert dukpy.run(entry, offset=2) == {
        "value": 42,
        "filename": entry.as_posix(),
        "dirname": tmp_path.as_posix(),
        "firstWrapperArgumentIsExports": True,
    }


def test_top_level_run_can_require_empty_commonjs_dependency(tmp_path):
    entry = tmp_path / "entry.js"
    dep = tmp_path / "empty.js"
    entry.write_text(
        "var empty = require('./empty');\n"
        "module.exports = {loaded: true, dependencyKeys: Object.keys(empty)};\n",
        encoding="utf-8",
    )
    dep.write_text("", encoding="utf-8")

    assert dukpy.run(entry) == {"loaded": True, "dependencyKeys": []}


def test_cli_run_preserves_node_like_core_fs_shim(monkeypatch, tmp_path, caplog):
    caplog.set_level(logging.INFO, logger="dukpy.interpreter")
    data = tmp_path / "data.txt"
    script = tmp_path / "script.js"
    data.write_text("read through fs shim", encoding="utf-8")
    script.write_text(
        "var fs = require('fs');\n"
        "console.log(fs.readFileSync(" + json.dumps(str(data)) + ", 'utf-8'));\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(sys, "argv", ["dukpy", str(script)])

    dukpy.cli.main()

    assert "read through fs shim" in caplog.messages


def test_entry_path_module_id_uses_registered_path_on_native_windows(monkeypatch):
    loader = dukpy.module_loader.JSModuleLoader()
    monkeypatch.setattr(dukpy.module_loader.os, "name", "nt")
    monkeypatch.setattr(dukpy.module_loader.os, "path", ntpath)
    loader.register_path(r"C:\project")

    path, module_id, module_format = loader.resolve_entry_path(r"C:\project\entry.cjs")

    assert path == r"C:\project\entry.cjs"
    assert module_id == "entry.cjs"
    assert module_format == "commonjs"


def test_commonjs_require_evaluates_detected_commonjs_dependency(tmp_path):
    dep = tmp_path / "dep.js"
    dep.write_text("exports.value = 42;\n", encoding="utf-8")

    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(tmp_path))

    assert interpreter.evaljs("require('dep.js').value") == 42


def test_commonjs_require_rejects_explicit_mjs_without_running_as_commonjs(tmp_path):
    dep = tmp_path / "dep.mjs"
    dep.write_text(
        "globalThis.requireExplicitMjsRan = true;\nmodule.exports = {value: 42};\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(tmp_path))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs("require('dep.mjs')")

    assert "require() of ES modules is not supported: dep.mjs" in str(exc.value)
    assert interpreter.evaljs("globalThis.requireExplicitMjsRan || false") is False


def test_commonjs_require_rejects_package_type_module_js_without_running(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "package.json").write_text('{"type": "module"}', encoding="utf-8")
    (package / "dep.js").write_text(
        "globalThis.requirePackageModuleRan = true;\nmodule.exports = {value: 42};\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(tmp_path))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs("require('package/dep.js')")

    assert "require() of ES modules is not supported: package/dep.js" in str(exc.value)
    assert interpreter.evaljs("globalThis.requirePackageModuleRan || false") is False


def test_commonjs_require_rejects_detected_esm_source(tmp_path):
    dep = tmp_path / "dep.js"
    dep.write_text("export const value = 42;\n", encoding="utf-8")

    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(tmp_path))

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs("require('dep.js')")

    assert "require() of ES modules is not supported: dep.js" in str(exc.value)
    assert "SyntaxError" not in str(exc.value)


def test_jsinterpreter_run_executes_mjs_static_import(tmp_path):
    entry = tmp_path / "entry.mjs"
    dep = tmp_path / "dep.mjs"
    entry.write_text(
        "import { value } from './dep.mjs';\n"
        "globalThis.runMjsStaticImport = value + dukpy.offset;\n",
        encoding="utf-8",
    )
    dep.write_text("export const value = 40;\n", encoding="utf-8")

    interpreter = dukpy.JSInterpreter()
    assert interpreter.run(entry, offset=2) == {}
    assert interpreter.evaljs("globalThis.runMjsStaticImport") == 42


def test_jsinterpreter_run_uses_loader_module_id_for_commonjs_entry_cache(tmp_path):
    entry = tmp_path / "entry.js"
    entry.write_text(
        "globalThis.runEntrySelfRequireCount = "
        "(globalThis.runEntrySelfRequireCount || 0) + 1;\n"
        "require('./entry');\n"
        "module.exports = {count: globalThis.runEntrySelfRequireCount};\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(tmp_path))

    assert interpreter.run(entry) == {"count": 1}
    assert interpreter.evaljs("globalThis.runEntrySelfRequireCount") == 1


def test_jsinterpreter_run_uses_loader_module_id_for_esm_entry_cache(tmp_path):
    entry = tmp_path / "entry.mjs"
    entry.write_text(
        "import './entry.mjs';\n"
        "globalThis.runEntrySelfImportCount = "
        "(globalThis.runEntrySelfImportCount || 0) + 1;\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    interpreter.loader.register_path(str(tmp_path))

    assert interpreter.run(entry) == {}
    assert interpreter.evaljs("globalThis.runEntrySelfImportCount") == 1


def test_jsinterpreter_run_uses_compile_probe_for_ambiguous_js_esm(tmp_path):
    entry = tmp_path / "entry.js"
    entry.write_text(
        "export const value = 42;\n"
        "globalThis.runAmbiguousJsEsm = {value, url: import.meta.url};\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    assert interpreter.run(entry) == {}
    assert interpreter.evaljs("globalThis.runAmbiguousJsEsm") == {
        "value": 42,
        "url": entry.as_posix(),
    }


def test_jsinterpreter_run_probes_ambiguous_js_with_commonjs_wrapper_shape(
    tmp_path,
):
    entry = tmp_path / "entry.js"
    entry.write_text(
        "let __filename = 'module lexical binding';\n"
        "let __dirname = 'module lexical binding';\n"
        "globalThis.runAmbiguousJsCommonJsWrapperProbe = this === undefined;\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    assert interpreter.run(entry) == {}
    assert interpreter.evaljs("globalThis.runAmbiguousJsCommonJsWrapperProbe") is True


def test_esm_import_probes_package_less_ambiguous_js_dependency(tmp_path):
    entry = tmp_path / "entry.mjs"
    dep = tmp_path / "dep.js"
    entry.write_text(
        "import { v } from './dep.js';\nglobalThis.runPackageLessAmbiguousJsDep = v;\n",
        encoding="utf-8",
    )
    dep.write_text("export const v = 42;\n", encoding="utf-8")

    interpreter = dukpy.JSInterpreter()
    assert interpreter.run(entry) == {}
    assert interpreter.evaljs("globalThis.runPackageLessAmbiguousJsDep") == 42


def test_commonjs_package_js_dependency_does_not_fallback_to_module(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "package.json").write_text('{"type": "commonjs"}', encoding="utf-8")
    entry = package / "entry.mjs"
    dep = package / "dep.js"
    entry.write_text("import './dep.js';\n", encoding="utf-8")
    dep.write_text("export const v = 42;\n", encoding="utf-8")

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.JSInterpreter().run(entry)

    assert "SyntaxError" in str(exc.value)


def test_module_package_js_dependency_uses_module_without_probe(tmp_path):
    package = tmp_path / "package"
    package.mkdir()
    (package / "package.json").write_text('{"type": "module"}', encoding="utf-8")
    entry = package / "entry.mjs"
    dep = package / "dep.js"
    entry.write_text("import './dep.js';\n", encoding="utf-8")
    dep.write_text(
        "globalThis.runModulePackageJsDepIsModule = this === undefined;\n",
        encoding="utf-8",
    )

    interpreter = dukpy.JSInterpreter()
    assert interpreter.run(entry) == {}
    assert interpreter.evaljs("globalThis.runModulePackageJsDepIsModule") is True
