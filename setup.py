#!/usr/bin/env python
import os
from setuptools import Extension, setup

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
        )
    ],
)
