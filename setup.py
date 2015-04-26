import os
from distutils.core import setup, Extension


duktape = Extension('dukpy._dukpy',
                    define_macros=[('DUK_OPT_DEEP_C_STACK', '1')],
                    sources=[os.path.join('duktape', 'duktape.c'), 
                             'pyduktape.c'],
                    include_dirs=[os.path.join('.', 'duktape')])

setup(
    name='dukpy',
    version='0.0.1',
    description='Simple JavaScript interpreter for Python',
    packages=['dukpy'],
    ext_modules=[duktape],
    package_data={
        'dukpy': ['*.js'],
    }
)
