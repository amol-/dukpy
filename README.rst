dukpy
=====

.. image:: https://img.shields.io/travis/amol-/dukpy/master.svg?label=Linux%20build%20%40%20Travis%20CI
    :target: https://travis-ci.org/amol-/dukpy

.. image:: https://img.shields.io/appveyor/ci/amol-/dukpy/master.svg?label=Windows%20build%20%40%20Appveyor
    :target: https://ci.appveyor.com/project/amol-/dukpy

.. image:: https://coveralls.io/repos/amol-/dukpy/badge.png?branch=master
    :target: https://coveralls.io/r/amol-/dukpy?branch=master

.. image:: https://img.shields.io/pypi/v/dukpy.svg
   :target: https://pypi.org/p/dukpy


DukPy is a simple javascript interpreter for Python built on top of
duktape engine **without any external dependency**.
It comes with a bunch of common transpilers built-in for convenience:

    - *CoffeeScript*
    - *BabelJS*
    - *TypeScript*
    - *JSX*
    - *LESS*

Dukpy has been tested on **Python 2.7** and **Python 3.4**, dukpy
is currently not production ready and might actually crash your
program as it is mostly implemented in C.

CoffeeScript Compiler
---------------------

Using the coffeescript compiler is as easy as running:

.. code:: python

    >>> import dukpy
    >>> dukpy.coffee_compile('''
    ...     fill = (container, liquid = "coffee") ->
    ...         "Filling the #{container} with #{liquid}..."
    ... ''')
    '(function() {\n  var fill;\n\n  fill = function*(container, liquid) {\n    if (liquid == null) {\n      liquid = "coffee";\n    }\n    return "Filling the " + container + " with " + liquid + "...";\n  };\n\n}).call(this);\n'

TypeScript Transpiler
---------------------

The TypeScript compiler can be used through the
``dukpy.typescript_compile`` function:

.. code:: python

    >>> import dukpy
    >>> dukpy.typescript_compile('''
    ... class Greeter {
    ...     constructor(public greeting: string) { }
    ...     greet() {
    ...         return "<h1>" + this.greeting + "</h1>";
    ...     }
    ... };
    ...
    ... var greeter = new Greeter("Hello, world!");
    ... ''')
    'var Greeter = (function () {\n    function Greeter(greeting) {\n        this.greeting = greeting;\n    }\n    Greeter.prototype.greet = function () {\n        return "<h1>" + this.greeting + "</h1>";\n    };\n    return Greeter;\n})();\n;\nvar greeter = new Greeter("Hello, world!");\n'

Currently the compiler has built-in options and doesn't accept additional ones,

The DukPY based TypeScript compiler also provides a WebAssets (
http://webassets.readthedocs.org/en/latest/ ) filter to automatically
compile TypeScript code in your assets pipeline.  You register this filter as
``typescript`` within WebAssets using:

.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import TypeScript

    register_filter(TypeScript)

Which makes the filter available with the ``typescript`` name.

**NOTE:** When using the TypeScript compiler for code that needs to run
in the browser, make sure to add
https://cdnjs.cloudflare.com/ajax/libs/systemjs/0.19.24/system.js
dependency. As ``import`` statements are resolved using SystemJS.

EcmaScript6 BabelJS Transpiler
------------------------------

To compile ES6 code to ES5 for everyday usage you can use
``dukpy.babel_compile``:

.. code:: python

    >>> import dukpy
    >>> dukpy.babel_compile('''
    ... class Point {
    ...     constructor(x, y) {
    ...             this.x = x;
    ...         this.y = y;
    ...         }
    ...         toString() {
    ...             return '(' + this.x + ', ' + this.y + ')';
    ...         }
    ... }
    ... ''')
    '"use strict";\n\nvar _prototypeProperties = function (child, staticProps, instanceProps) { if (staticProps) Object.defineProperties(child, staticProps); if (instanceProps) Object.defineProperties(child.prototype, instanceProps); };\n\nvar _classCallCheck = function (instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } };\n\nvar Point = (function () {\n    function Point(x, y) {\n        _classCallCheck(this, Point);\n\n        this.x = x;\n        this.y = y;\n    }\n\n    _prototypeProperties(Point, null, {\n        toString: {\n            value: function toString() {\n                return "(" + this.x + ", " + this.y + ")";\n            },\n            writable: true,\n            configurable: true\n        }\n    });\n\n    return Point;\n})();\n'

You  can pass `options`__ to the BabelJS compiler just as keywords on
the call to ``babel_compile()``.

__ http://babeljs.io/docs/usage/options/

The DukPY based BabelJS compiler also provides a WebAssets (
http://webassets.readthedocs.org/en/latest/ ) filter to automatically
compile ES6 code in your assets pipeline.  You register this filter as
``babeljs`` within WebAssets using:

.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import BabelJS

    register_filter(BabelJS)

Which makes the filter available with the ``babeljs`` name.
Only supported filter option is currently `BABEL_MODULES_LOADER` with value
``systemjs`` or ``umd`` to specify that compiled code should use SystemJS
or UMD instead of CommonJS for modules.

**NOTE:** When using the BabelJS compiler for code that needs to run
in the browser, make sure to add
https://cdnjs.cloudflare.com/ajax/libs/babel-polyfill/6.13.0/polyfill.min.js
dependency.

JSX to React Transpiling
------------------------

DukPy provides a built-in compiler from JSX to React, this is available as
``dukpy.jsx_compile``:

.. code:: python

    >>> import dukpy
    >>> dukpy.jsx_compile('var react_hello = <h1>Hello, world!</h1>;')
    u'"use strict";\n\nvar react_hello = React.createElement(\n  "h1",\n  null,\n  "Hello, world!"\n);'

The DukPY based JSX compiler also provides a WebAssets (
http://webassets.readthedocs.org/en/latest/ ) filter to automatically
compile JSX+ES6 code in your assets pipeline.  You register this filter as
``babeljsx`` within WebAssets using:

.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import BabelJSX

    register_filter(BabelJSX)

Which makes the filter available with the ``babeljsx`` name.
This filter supports the same options as the babel one.

Less Transpiling
----------------

DukPy provides a built-in distribution of the less compiler available
through `dukpy.less_compile`:

.. code:: python

    >>> import dukpy
    >>> dukpy.less_compile('.class { width: (1 + 1) }')
    '.class {\n  width: 2;\n}\n'


The DukPY based LESS compiler also provides a WebAssets (
http://webassets.readthedocs.org/en/latest/ ) filter to automatically
compile LESS code in your assets pipeline.  You register this filter as
``lessc`` within WebAssets using:

.. code:: python

    from webassets.filter import register_filter
    from dukpy.webassets import CompileLess

    register_filter(CompileLess)

Which makes the filter available with the ``lessc`` name.


Using the JavaScript Interpreter
--------------------------------

Using dukpy is as simple as calling the ``dukpy.evaljs`` function with
the javascript code:

.. code:: python

    >>> import dukpy
    >>> dukpy.evaljs("var o = {'value': 5}; o['value'] += 3; o")
    {'value': 8}


The ``evaljs`` function executes the javascript and returns the
resulting value as far as it is possible to encode it in JSON.

If execution fails a ``dukpy.JSRuntimeError`` exception is raised
with the failure reason.

Passing Arguments
~~~~~~~~~~~~~~~~~

Any argument passed to ``evaljs`` is available in JavaScript inside
the ``dukpy`` object in javascript. It must be possible to encode
the arguments using JSON for them to be available in Javascript:

.. code:: python

    >>> import dukpy
    >>>
    >>> def sum3(value):
    ...     return dukpy.evaljs("dukpy['value'] + 3", value=value)
    ...
    >>> sum3(7)
    10

Running Multiple Scripts
~~~~~~~~~~~~~~~~~~~~~~~~

The ``evaljs`` function supports providing multiple source codes to
be executed in the same context.

Multiple script can be passed in a list or tuple:

.. code:: python

    >>> import dukpy
    >>> dukpy.evaljs(["var o = {'value': 5}",
    ...               "o['value'] += 3",
    ...               "o"])
    {'value': 8}

This is useful when your code requires dependencies to work,
as you can load the dependency and then your code.

This is actually how the coffeescript compiler is implemented
by DukPy itself:

.. code:: python

    def coffee_compile(source):
        with open(COFFEE_COMPILER, 'r') as coffeescript_js:
            return evaljs((coffeescript_js.read(), 'CoffeeScript.compile(dukpy.coffeecode)'),
                          coffeecode=source)

Using a persistent JavaScript Interpreter
-----------------------------------------

The ``evaljs`` function creates a new interpreter on each call,
this is usually convenient and avoid errors due to dirt global variables
or unexpected execution status.

In some cases you might want to run code that has a slow bootstrap, so
it's convenient to reuse the same interpreter between two different calls
so that the bootstrap cost has already been paid during the first execution.

This can be achieved by using the ``dukpy.JSInterpreter`` object.

Creating a ``dukpy.JSInterpreter`` permits to evaluate code inside that interpreter
and multiple ``eval`` calls will share the same interpreter and global status:


.. code:: python

    >>> import dukpy
    >>> interpreter = dukpy.JSInterpreter()
    >>> interpreter.evaljs("var o = {'value': 5}; o")
    {u'value': 5}
    >>> interpreter.evaljs("o.value += 1; o")
    {u'value': 6}

Loading modules with require
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using the ``dukpy.JSInterpreter`` object it is possible to use
the ``require('modulename')`` instruction to load a module inside javascript.

Modules are looked up in all directories registered with
``dukpy.JSInterpreter.loader.register_path``:

.. code:: python

    >>> import dukpy
    >>> jsi = dukpy.JSInterpreter()
    >>> jsi.loader.register_path('./js_modules')
    >>> jsi.evaljs("isEmpty = require('fbjs/lib/isEmpty'); isEmpty([1])")
    False

Installing packages from npmjs.org
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When using the persistent javascript interpreter it is also possible to install packages
from *npmjs.org* through the ``dukpy.install_jspackage`` function:

.. code:: python

    >>> import dukpy
    >>> jsi = dukpy.JSInterpreter()
    >>> dukpy.install_jspackage('promise', None, './js_modules')
    Packages going to be installed: promise->7.1.1, asap->2.0.3
    Fetching https://registry.npmjs.org/promise/-/promise-7.1.1.tgz..........................
    Fetching https://registry.npmjs.org/asap/-/asap-2.0.3.tgz............
    Installing promise in ./js_modules Done!

The same functionality is also provided by the ``dukpy-install`` shell command::

    $ dukpy-install -d ./js_modules promise
    Packages going to be installed: promise->7.1.1, asap->2.0.3
    Fetching https://registry.npmjs.org/promise/-/promise-7.1.1.tgz..........................
    Fetching https://registry.npmjs.org/asap/-/asap-2.0.3.tgz............
    Installing promise in ./js_modules Done!

Please note that currently `install_jspackage` is not able to resolve conflicting
dependencies.
