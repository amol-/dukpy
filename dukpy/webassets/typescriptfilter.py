# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from webassets.filter import Filter

import dukpy


__all__ = ('TypeScript', )


class TypeScript(Filter):
    name = 'typescript'
    max_debug_level = None

    def input(self, _in, out, **kw):
        src = dukpy.typescript_compile(_in.read())
        out.write(src)
