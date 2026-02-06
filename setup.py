#!/usr/bin/env python
import os
from setuptools import Extension, setup

setup(
    ext_modules=[
        Extension(
            "dukpy._dukpy",
            define_macros=[
                ("DUK_OPT_NONSTD_REGEXP_DOLLAR_ESCAPE", "1"),
                ("DUK_OPT_OCTAL_SUPPORT", "1"),
            ],
            sources=[
                os.path.join("src", "duktape", "duktape.c"),
                os.path.join("src", "duktape", "duk_v1_compat.c"),
                os.path.join("src", "duktape", "duk_module_duktape.c"),
                os.path.join("src", "quickjs", "quickjs-amalgam.c"),
                os.path.join("src", "_support.c"),
                os.path.join("src", "dukpyjs.c"),
            ],
            include_dirs=[
                os.path.join(".", "src", "duktape"),
                os.path.join(".", "src", "quickjs"),
            ],
        )
    ],
)
