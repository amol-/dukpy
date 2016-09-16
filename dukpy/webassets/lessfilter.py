# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function

import os

from webassets.filter import Filter, option

import dukpy


__all__ = ('CompileLess', )


class CompileLess(Filter):
    name = 'lessc'
    max_debug_level = None
    options = {
        'less_includes': option('LIBSASS_INCLUDES', type=list)
    }

    def input(self, _in, out, **kw):
        options = {'paths': []}
        if self.less_includes:
            options['paths'].extend(self.less_includes)
        if 'source_path' in kw:
            options['paths'].append(os.path.dirname(kw['source_path']))

        src = dukpy.less_compile(_in.read(), options=options)
        out.write(src)
