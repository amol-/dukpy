import dukpy


class TestJSInterpreter(object):
    def test_interpreter_keeps_context(self):
        interpreter = dukpy.JSInterpreter()
        ans = interpreter.eval("var o = {'value': 5}; o")
        assert ans == {'value': 5}
        ans = interpreter.eval("o.value += 1; o")
        assert ans == {'value': 6}
