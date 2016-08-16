# -*- coding: utf-8 -*-
import os
from .evaljs import JSInterpreter


class NodeLikeInterpreter(JSInterpreter):
    """A DukPy Interpreter that provides a minimal compatibility layer with NodeJS"""
    def __init__(self):
        super(NodeLikeInterpreter, self).__init__()
        self.loader.register_path(os.path.join(os.path.dirname(__file__), 'jscore'))
        self.export_function('file.exists', FS.exists)
        self.export_function('file.read', FS.read)


class FS:
    """Provides oversimplified fs.js native functions."""
    @classmethod
    def exists(cls, filepath):
        try:
            os.stat(filepath)
            return True
        except:
            return False

    @classmethod
    def read(cls, path, encoding):
        with open(path, 'rb') as f:
            data = f.read()

        if encoding is not None:
            return data.decode(encoding)
        else:
            return data
