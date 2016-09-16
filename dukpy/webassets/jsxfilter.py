# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function
from webassets.filter import Filter

import dukpy


__all__ = ('BabelJSX', )


class BabelJSX(Filter):
    name = 'babeljsx'
    max_debug_level = None
    options = {
        'loader': 'BABEL_MODULES_LOADER'
    }

    def input(self, _in, out, **kw):
        options = {}
        if self.loader == 'systemjs':
            options['plugins'] = ['transform-es2015-modules-systemjs']
        src = dukpy.jsx_compile(_in.read(), **options)
        out.write(src)
