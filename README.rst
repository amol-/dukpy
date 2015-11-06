dukpy
=====

.. image:: https://travis-ci.org/amol-/dukpy.png?branch=master 
    :target: https://travis-ci.org/amol-/dukpy 

.. image:: https://coveralls.io/repos/amol-/dukpy/badge.png?branch=master
    :target: https://coveralls.io/r/amol-/dukpy?branch=master 

DukPy is a simple javascript interpreter for Python built on top of
duktape engine **without any external dependency**.
It comes with a builtin *CoffeeScript* compiler for
convenience and usage example.

Dukpy has been tested on **Python 2.7** and **Python 3.4**, dukpy
is currently not production ready and might actually crash your
program as it is mostly implemented in C.

CoffeeScript Compiler
---------------------

Using the coffeescript compiler is as easy as running::

    >>> import dukpy
    >>> dukpy.coffee_compile('''
    ...     fill = (container, liquid = "coffee") ->
    ...         "Filling the #{container} with #{liquid}..."
    ... ''')
    '(function() {\n  var fill;\n\n  fill = function*(container, liquid) {\n    if (liquid == null) {\n      liquid = "coffee";\n    }\n    return "Filling the " + container + " with " + liquid + "...";\n  };\n\n}).call(this);\n'

EcmaScript6 BabelJS Transpiler
------------------------------

To compile ES6 code to ES5 for everyday usage you can use ``dukpy.babel_compile``::

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

The DukPY based BabelJS compiler also provides a WebAssets ( http://webassets.readthedocs.org/en/latest/ ) filter to automatically compile ES6 code in your assets pipeline.
You register this filter as ``babeljs`` within WebAssets using::

    from webassets.filter import register_filter
    from dukpy.webassets.babelfilter import BabelJS
    
    register_filter(BabelJS)

Which makes the filter available with the ``babeljs`` name.

**NOTE:** When using the BabelJS compiler for code that needs to run in the browser, make sure to add https://cdnjs.cloudflare.com/ajax/libs/babel-core/4.6.6/browser-polyfill.js dependency.

Using the JavaScript Interpreter
--------------------------------

Using dukpy is as simple as calling the ``dukpy.evaljs`` function with
the javascript code::

    >>> import dukpy
    >>> dukpy.evaljs("var o = {'value': 5}; o['value'] += 3; o")
    {'value': 8}


The ``evaljs`` function executes the javascript and returns the
resulting value as far as it is possible to encode it in JSON.

If execution fails a ``dukpy.JSRuntimeError`` exception is raised
with the failure reason.

Passing Arguments
-----------------

Any argument passed to ``evaljs`` is available in JavaScript inside
the ``dukpy`` object in javascript. It must be possible to encode
the arguments using JSON for them to be available in Javascript::

    >>> import dukpy
    >>>
    >>> def sum3(value):
    ...     return dukpy.evaljs("dukpy['value'] + 3", value=value)
    ...
    >>> sum3(7)
    10

Running Multiple Scripts
------------------------

The ``evaljs`` function supports providing multiple source codes to
be executed in the same context.

Multiple script can be passed in a list or tuple::

    >>> import dukpy
    >>> dukpy.evaljs(["var o = {'value': 5}",
    ...               "o['value'] += 3",
    ...               "o"])
    {'value': 8}

This is useful when your code requires dependencies to work,
as you can load the dependency and then your code.

This is actually how the coffeescript compiler is implemented
by DukPy itself::

    def coffee_compile(source):
        with open(COFFEE_COMPILER, 'r') as coffeescript_js:
            return evaljs((coffeescript_js.read(), 'CoffeeScript.compile(dukpy.coffeecode)'),
                          coffeecode=source)
