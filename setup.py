#!/usr/bin/env python
import os
import sys
from setuptools import Extension, setup

if sys.platform == "win32":
    extra_compile_args = ["/std:c11", "/experimental:c11atomics"]
    # MSVC keeps __STDC_NO_ATOMICS__ defined even when its experimental
    # C11 atomics support is enabled, so enable QuickJS atomics explicitly.
    define_macros = [("CONFIG_ATOMICS", "1")]
elif sys.platform.startswith("linux"):
    extra_compile_args = ["-std=c11"]
    define_macros = [("_GNU_SOURCE", "1")]
else:
    extra_compile_args = ["-std=c11"]
    define_macros = []

setup(
    ext_modules=[
        Extension(
            "dukpy._dukpy",
            sources=[
                os.path.join("src", "quickjs", "quickjs-amalgam.c"),
                os.path.join("src", "_support.c"),
                os.path.join("src", "dukpyjs.c"),
            ],
            include_dirs=[
                os.path.join(".", "src", "quickjs"),
            ],
            extra_compile_args=extra_compile_args,
            define_macros=define_macros,
        )
    ],
)
