from dukpy._dukpy import JSRuntimeError

import dukpy
from diffreport import report_diff


class TestJSInterpreter(object):
    def test_interpreter_keeps_context(self):
        interpreter = dukpy.JSInterpreter()
        ans = interpreter.evaljs("var o = {'value': 5}; o")
        assert ans == {'value': 5}
        ans = interpreter.evaljs("o.value += 1; o")
        assert ans == {'value': 6}

    def test_call_python(self):
        def _say_hello(num, who):
            return 'Hello ' + ' '.join([who]*num)

        interpreter = dukpy.JSInterpreter()
        interpreter.export_function('say_hello', _say_hello)
        res = interpreter.evaljs("call_python('say_hello', 3, 'world')")
        assert res == 'Hello world world world', res

    def test_module_loader(self):
        interpreter = dukpy.JSInterpreter()
        res = interpreter.evaljs('''
    babel = require('babel-6.14.0.min');
    babel.transform(dukpy.es6code, {presets: ["es2015"]}).code;
''', es6code='let i=5;')

        expected = '''"use strict";

var i = 5;'''
        assert res == expected, report_diff(expected, res)

    def test_module_loader_unexisting(self):
        interpreter = dukpy.JSInterpreter()

        try:
            interpreter.evaljs("require('missing_module');")
        except JSRuntimeError as e:
            assert 'cannot find module: missing_module' in str(e)
        else:
            assert False, 'should have raised'