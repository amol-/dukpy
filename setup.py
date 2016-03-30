import os
from distutils.core import setup, Extension

HERE = os.path.abspath(os.path.dirname(__file__))
try:
    README = open(os.path.join(HERE, 'README.rst')).read()
except IOError:
    README = ''

duktape = Extension('dukpy._dukpy',
                    define_macros=[('DUK_OPT_DEEP_C_STACK', '1')],
                    sources=[os.path.join('duktape', 'duktape.c'), 
                             'pyduktape.c'],
                    include_dirs=[os.path.join('.', 'duktape')])

setup(
    name='dukpy',
    version='0.0.2',
    description='Simple JavaScript interpreter for Python',
    long_description=README,
    keywords='javascript compiler babeljs coffeescript typescript',
    author='Alessandro Molina',
    author_email='alessandro.molina@axant.it',
    url='https://github.com/amol-/dukpy',
    license='MIT',
    packages=['dukpy', 'dukpy.webassets'],
    ext_modules=[duktape],
    package_data={
        'dukpy': ['*.js'],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: JavaScript',
    ]
)
