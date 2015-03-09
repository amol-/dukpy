import os
from distutils.core import setup, Extension


duktape = Extension('_dukpy',
                    sources = [os.path.join('duktape', 'duktape.c'), 
                               'pyduktape.c'],
                    include_dirs=[os.path.join('.', 'duktape')])

setup(
    name='dukpy',
    version = '0.0.1',
    description = 'Simple JavaScript interpreter for Python',
    ext_modules = [duktape]
)
