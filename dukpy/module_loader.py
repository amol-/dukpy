# -*- coding: utf-8 -*-
import json
import os


class JSModuleLoader(object):
    """Manages finding and loading JS modules in CommonJS format.

    This allows to import a module from JSInterpreter using the
    `require('modulename')` command.

    To register additional paths where to look for modules use
    the `JSModuleLoader.register_path` method.
    """
    def __init__(self):
        self._paths = []
        self.register_path(os.path.join(os.path.dirname(__file__), 'jsmodules'))
        self.register_path(os.getcwd())

    def register_path(self, path):
        """Registers a directory where to look for modules.

        By default only modules relative to current path are found.
        """
        self._paths.insert(0, os.path.abspath(path))

    def lookup(self, module_name):
        """Searches for a file providing given module."""
        for search_path in self._paths:
            module_path = os.path.join(search_path, module_name)
            module_file = self._lookup(module_path)
            if module_file:
                return module_file

    def load(self, module_name):
        """Returns source code of the given module."""
        path = self.lookup(module_name)
        if path:
            with open(path, 'rb') as f:
                return f.read()

    def _lookup(self, module_path):
        # Module is a plain .js file
        for path in (module_path, os.path.extsep.join((module_path, 'js'))):
            if os.path.exists(path) and os.path.isfile(path):
                return path

        # Module is a package
        package = os.path.join(module_path, os.path.extsep.join(('package', 'json')))
        try:
            with open(package) as f:
                package = json.load(f)
        except IOError:
            pass
        else:
            package_main = package.get('main')
            if package_main:
                path = self._lookup(os.path.join(module_path, package_main))
                if path:
                    return path

        # Module is directory with index.js inside
        indexjs = os.path.join(module_path, os.path.extsep.join(('index', 'js')))
        if os.path.exists(indexjs):
            return indexjs
