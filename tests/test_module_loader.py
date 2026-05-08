from dukpy.module_loader import JSModuleLoader


# TODO(EVO-190): Replace loader tuple checks with runtime module-format acceptance.
# Current tests assert JSModuleLoader.load(...) return tuples directly. Finish by
# moving module-format coverage to acceptance fixtures that import/require real
# packages for .mjs, .cjs, package.json type=module/commonjs, extensionless
# misses, and missing modules. Keep only small unit tests for path-resolution
# helpers that cannot be observed through the public interpreter API.


def test_load_returns_commonjs_for_js_by_default_without_source_sniffing(tmp_path):
    module_path = tmp_path / "pkg" / "metadata.js"
    module_path.parent.mkdir()
    source = """// import/export/await in a comment must not affect format.
const text = "import value from './dep'; export default value; await value";
/* export const blockCommentToken = await import('./dep'); */
module.exports = text;
"""
    module_path.write_text(source, encoding="utf-8")

    loader = JSModuleLoader()
    loader.register_path(str(tmp_path))

    assert loader.load("pkg/metadata") == (
        "pkg/metadata.js",
        source,
        "commonjs",
    )


def test_load_resolves_explicit_mjs_and_cjs_file_formats(tmp_path):
    (tmp_path / "esm_only.mjs").write_text(
        "export const value = 1;\n", encoding="utf-8"
    )
    (tmp_path / "cjs_only.cjs").write_text("module.exports = 1;\n", encoding="utf-8")

    loader = JSModuleLoader()
    loader.register_path(str(tmp_path))

    assert loader.load("esm_only.mjs") == (
        "esm_only.mjs",
        "export const value = 1;\n",
        "module",
    )
    assert loader.load("cjs_only.cjs") == (
        "cjs_only.cjs",
        "module.exports = 1;\n",
        "commonjs",
    )


def test_load_does_not_probe_mjs_or_cjs_for_extensionless_names(tmp_path):
    (tmp_path / "esm_only.mjs").write_text(
        "export const value = 1;\n", encoding="utf-8"
    )
    (tmp_path / "cjs_only.cjs").write_text("module.exports = 1;\n", encoding="utf-8")

    loader = JSModuleLoader()
    loader.register_path(str(tmp_path))

    assert loader.load("esm_only") == (None, None, None)
    assert loader.load("cjs_only") == (None, None, None)


def test_load_uses_nearest_package_type_for_js_package_mains_without_sniffing(tmp_path):
    package_path = tmp_path / "pkg"
    nested_path = package_path / "nested"
    nested_path.mkdir(parents=True)
    (package_path / "package.json").write_text(
        '{"type": "module", "main": "main.js"}\n', encoding="utf-8"
    )
    (package_path / "main.js").write_text("module.exports = 1;\n", encoding="utf-8")
    (nested_path / "package.json").write_text(
        '{"type": "commonjs", "main": "main.js"}\n', encoding="utf-8"
    )
    (nested_path / "main.js").write_text("export const value = 1;\n", encoding="utf-8")

    loader = JSModuleLoader()
    loader.register_path(str(tmp_path))

    assert loader.load("pkg") == (
        "pkg/main.js",
        "module.exports = 1;\n",
        "module",
    )
    assert loader.load("pkg/nested") == (
        "pkg/nested/main.js",
        "export const value = 1;\n",
        "commonjs",
    )


def test_load_keeps_extension_format_over_package_type(tmp_path):
    module_package = tmp_path / "module_pkg"
    commonjs_package = tmp_path / "commonjs_pkg"
    module_package.mkdir()
    commonjs_package.mkdir()
    (module_package / "package.json").write_text(
        '{"type": "module"}\n', encoding="utf-8"
    )
    (commonjs_package / "package.json").write_text(
        '{"type": "commonjs"}\n', encoding="utf-8"
    )
    (module_package / "explicit.cjs").write_text(
        "module.exports = 1;\n", encoding="utf-8"
    )
    (commonjs_package / "explicit.mjs").write_text(
        "export const value = 1;\n", encoding="utf-8"
    )

    loader = JSModuleLoader()
    loader.register_path(str(tmp_path))

    assert loader.load("module_pkg/explicit.cjs") == (
        "module_pkg/explicit.cjs",
        "module.exports = 1;\n",
        "commonjs",
    )
    assert loader.load("commonjs_pkg/explicit.mjs") == (
        "commonjs_pkg/explicit.mjs",
        "export const value = 1;\n",
        "module",
    )


def test_load_returns_empty_metadata_for_missing_module(tmp_path):
    loader = JSModuleLoader()
    loader.register_path(str(tmp_path))

    assert loader.load("missing") == (None, None, None)
