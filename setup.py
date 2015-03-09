import os
from distutils.core import setup, Extension


duktape = Extension('dukpy._dukpy',
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
