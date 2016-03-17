# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from webassets.filter import Filter

import dukpy


__all__ = ('BabelJS', )


class BabelJS(Filter):
    name = 'babeljs'
    max_debug_level = None

    def input(self, _in, out, **kw):
        src = dukpy.babel_compile(_in.read())
        out.write(src['code'])
