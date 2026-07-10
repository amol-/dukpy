# -*- coding: utf-8 -*-
"""Metadata-only JavaScript module resolution.

``JSModuleLoader`` finds module source files and returns the format metadata
that tells QuickJS whether DukPy intends native ES module, CommonJS handling, or
QuickJS wrapper probing for ambiguous ``.js`` files. The loader owns only
metadata-based classification: explicit ``.mjs`` and ``.cjs`` extensions,
nearest ``package.json`` ``type`` for ``.js`` files, and a CommonJS default. It
never scans JavaScript source for syntax-looking text.
"""

import json
import os


class JSModuleLoader(object):
    """Manages finding and loading JS modules.

    This allows to import a module from JSInterpreter using the
    `require('modulename')` command.

    To register additional paths where to look for modules use
    the `JSModuleLoader.register_path` method.
    """

    def __init__(self):
        self._paths = []
        self.register_path(os.path.join(os.path.dirname(__file__), "jsmodules"))
        self.register_path(os.getcwd())

    def register_path(self, path):
        """Registers a directory where to look for modules.

        By default only modules relative to current path are found.
        """
        self._paths.insert(0, os.path.abspath(path))

    def lookup(self, module_name):
        """Searches for a file providing given module.

        Returns the normalized module id and path of the file.
        """
        module_id, path, _ = self._lookup(module_name)
        return module_id, path

    def load(self, module_name):
        """Returns normalized id, source code, and format of the given module.

        Only supports source code files encoded as UTF-8.
        """
        module_id, path, module_format = self._lookup(module_name)
        if path:
            with open(path, "rb") as f:
                return module_id, f.read().decode("utf-8"), module_format
        return None, None, None

    def resolve_entry_path(self, path):
        """Return absolute path, canonical module id, and format for an entrypoint."""
        path = os.path.abspath(os.fspath(path))
        return path, self._module_id(path), self.format_for_path(path)

    def format_for_path(self, path):
        """Return explicit Node-like format metadata for a JavaScript path.

        Ambiguous package-less ``.js`` files return ``"detect"`` so QuickJS can
        probe the CommonJS wrapper before deciding between CommonJS and native
        ES module compilation.
        """
        extension = os.path.splitext(path)[1]
        if extension == ".mjs":
            return "module"
        if extension == ".cjs":
            return "commonjs"
        if extension == ".js":
            package_type = self._package_type(path)
            return package_type if package_type in ("commonjs", "module") else "detect"
        return "commonjs"

    def _lookup(self, module_name):
        for search_path in self._paths:
            module_file, module_format = self._resolve(
                os.path.join(search_path, module_name)
            )
            if module_file:
                return self._module_id(module_file), module_file, module_format
        return None, None, None

    def _resolve(self, module_path, seen=None):
        module_file, module_format = self._resolve_file(module_path)
        if module_file:
            return module_file, module_format
        return self._resolve_directory(module_path, seen or set())

    def _resolve_file(self, module_path):
        for path in (module_path, os.path.extsep.join((module_path, "js"))):
            if os.path.isfile(path):
                return path, self.format_for_path(path)
        return None, None

    def _resolve_directory(self, module_path, seen):
        if not os.path.isdir(module_path):
            return None, None

        real_path = os.path.realpath(module_path)
        if real_path in seen:
            return None, None
        seen.add(real_path)

        package_path = os.path.join(
            module_path, os.path.extsep.join(("package", "json"))
        )
        try:
            with open(package_path, encoding="utf-8") as package_file:
                package = json.load(package_file)
        except (IOError, ValueError):
            package = {}

        package_main = package.get("main") if isinstance(package, dict) else None
        if isinstance(package_main, str) and package_main:
            module_file, module_format = self._resolve(
                os.path.join(module_path, package_main), seen
            )
            if module_file:
                return module_file, module_format

        return self._resolve_file(os.path.join(module_path, "index"))

    def _package_type(self, path):
        current = os.path.abspath(os.path.dirname(path))
        while True:
            package_path = os.path.join(
                current, os.path.extsep.join(("package", "json"))
            )
            if os.path.isfile(package_path):
                try:
                    with open(package_path, encoding="utf-8") as package_file:
                        package = json.load(package_file)
                except (IOError, ValueError):
                    return None
                package_type = (
                    package.get("type") if isinstance(package, dict) else None
                )
                return package_type if package_type in ("commonjs", "module") else None

            parent = os.path.dirname(current)
            if parent == current:
                return None
            current = parent

    def _module_id(self, module_file):
        module_file = os.path.realpath(module_file)
        relative_ids = []
        for search_path in self._paths:
            search_path = os.path.realpath(search_path)
            try:
                common_path = os.path.commonpath((search_path, module_file))
            except ValueError:
                continue
            if common_path == search_path:
                relative_ids.append(os.path.relpath(module_file, search_path))

        module_id = module_file
        for relative_id in sorted(
            set(relative_ids),
            key=lambda path: (len(path.split(os.path.sep)), len(path), path),
        ):
            for search_path in self._paths:
                candidate = os.path.join(os.path.realpath(search_path), relative_id)
                if (
                    os.path.isfile(candidate)
                    and os.path.realpath(candidate) != module_file
                ):
                    break
            else:
                module_id = relative_id
                break

        return self._path_id(module_id)

    def _path_id(self, path):
        if os.path.altsep:
            path = path.replace(os.path.altsep, "/")
        path = path.replace(os.path.sep, "/")
        if "\\" in path and (
            path.startswith("\\\\")
            or (len(path) >= 3 and path[1] == ":" and path[2] == "\\")
        ):
            path = path.replace("\\", "/")
        return path
