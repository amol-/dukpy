import dukpy


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