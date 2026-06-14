import unittest

from dukpy._dukpy import JSRuntimeError

import dukpy


class TestJSInterpreter(unittest.TestCase):
    def test_interpreter_keeps_context(self):
        interpreter = dukpy.JSInterpreter()
        ans = interpreter.evaljs("var o = {'value': 5}; o")
        assert ans == {"value": 5}
        ans = interpreter.evaljs("o.value += 1; o")
        assert ans == {"value": 6}

    def test_evaljs_reports_dukpy_global_publication_failure(self):
        interpreter = dukpy.JSInterpreter()
        assert interpreter.evaljs("Object.freeze(globalThis); 1") == 1

        with self.assertRaises(JSRuntimeError) as err:
            interpreter.evaljs("42", value=2)

        assert "TypeError: 'dukpy' is read-only" in str(err.exception)

    def test_evaljs_reports_call_python_global_publication_failure(self):
        interpreter = dukpy.JSInterpreter()
        assert (
            interpreter.evaljs(
                """
                Object.defineProperty(globalThis, 'call_python', {
                    value: call_python,
                    writable: false,
                    configurable: false
                });
                1;
                """
            )
            == 1
        )

        with self.assertRaises(JSRuntimeError) as err:
            interpreter.evaljs("42")

        assert "TypeError: 'call_python' is read-only" in str(err.exception)

    def test_call_python_preserves_argument_order_and_json_types(self):
        seen = []

        def bridge(*args):
            seen.append(args)
            return {
                "none": None,
                "true": True,
                "false": False,
                "int": 7,
                "float": 2.5,
                "text": "hello",
                "unicode": "雪☃",
                "list": [1, "two", None],
                "object": {"nested": "value"},
            }

        interpreter = dukpy.JSInterpreter()
        interpreter.export_function("bridge.types", bridge)
        res = interpreter.evaljs(
            """
            var value = call_python('bridge.types', 'first', 2, true, false, null,
                                    ['雪', 3], {nested: {answer: 42}});
            ({
                value: value,
                js_checks: [
                    value.none === null,
                    value.true === true,
                    value.false === false,
                    value.int === 7,
                    value.float === 2.5,
                    value.text === 'hello',
                    value.unicode === '雪☃',
                    value.list[2] === null,
                    value.object.nested === 'value'
                ]
            });
            """
        )
        assert seen == [
            (
                "first",
                2,
                True,
                False,
                None,
                ["雪", 3],
                {"nested": {"answer": 42}},
            )
        ]
        assert [type(arg) for arg in seen[0]] == [
            str,
            int,
            bool,
            bool,
            type(None),
            list,
            dict,
        ]
        assert type(seen[0][5][1]) is int
        assert type(seen[0][6]["nested"]["answer"]) is int
        assert res["js_checks"] == [True] * 9
        assert res["value"] == {
            "none": None,
            "true": True,
            "false": False,
            "int": 7,
            "float": 2.5,
            "text": "hello",
            "unicode": "雪☃",
            "list": [1, "two", None],
            "object": {"nested": "value"},
        }

    def test_call_python_accepts_unicode_function_names_and_values(self):
        interpreter = dukpy.JSInterpreter()
        interpreter.export_function(
            "工具.☃", lambda value: {"echo": value, "name": "工具.☃"}
        )

        assert interpreter.evaljs("call_python('工具.☃', '雪')") == {
            "echo": "雪",
            "name": "工具.☃",
        }

    def test_call_python_maps_python_none_return_to_javascript_undefined(self):
        interpreter = dukpy.JSInterpreter()
        interpreter.export_function("noop", lambda: None)

        assert interpreter.evaljs("typeof call_python('noop')") == "undefined"

    def test_call_python_arguments_follow_json_stringify_limits(self):
        seen = []

        def capture(*args):
            seen.append(args)
            return "ok"

        interpreter = dukpy.JSInterpreter()
        interpreter.export_function("capture", capture)

        assert (
            interpreter.evaljs(
                """
                call_python('capture',
                    [undefined, function(){}, Symbol('x'), NaN, Infinity],
                    {keep: 1, missing: undefined, fn: function(){},
                     sym: Symbol('x'), nan: NaN, inf: Infinity});
                """
            )
            == "ok"
        )
        assert seen == [
            ([None, None, None, None, None], {"keep": 1, "nan": None, "inf": None})
        ]

    def test_call_python_reports_argument_array_setup_failure_before_callback(self):
        seen = []

        def capture(*args):
            seen.append(args)
            return "unreached"

        interpreter = dukpy.JSInterpreter()
        interpreter.export_function("capture", capture)

        with self.assertRaises(JSRuntimeError) as err:
            interpreter.evaljs(
                """
                Object.defineProperty(Array.prototype, '0', {
                    value: 'blocked',
                    writable: false,
                    configurable: true
                });
                call_python('capture', 'arg');
                """
            )
        assert "TypeError: '0' is read-only" in str(err.exception)
        assert seen == []

    def test_call_python_rejects_arguments_json_stringify_cannot_emit(self):
        seen = []

        def capture(*args):
            seen.append(args)
            return "unreached"

        interpreter = dukpy.JSInterpreter()
        interpreter.export_function("capture", capture)

        with self.assertRaises(JSRuntimeError) as err:
            interpreter.evaljs(
                """
                var value = {};
                value.self = value;
                call_python('capture', value);
                """
            )
        assert "TypeError: circular reference" in str(err.exception)
        assert seen == []


    def test_call_python_missing_function_error_is_reference_error(self):
        interpreter = dukpy.JSInterpreter()

        assert interpreter.evaljs(
            """
            var caught = null;
            try {
                call_python('missing.☃');
            } catch (e) {
                caught = {name: e.name, message: e.message};
            }
            caught;
            """
        ) == {
            "name": "ReferenceError",
            "message": "No Python Function named missing.☃",
        }

    def test_call_python_propagates_python_exception_as_internal_error(self):
        def fail():
            raise ValueError("boom 雪")

        interpreter = dukpy.JSInterpreter()
        interpreter.export_function("fail", fail)

        assert interpreter.evaljs(
            """
            var caught = null;
            try {
                call_python('fail');
            } catch (e) {
                caught = {name: e.name, message: e.message};
            }
            caught;
            """
        ) == {
            "name": "InternalError",
            "message": (
                "Error while calling Python Function (fail): ValueError('boom 雪')"
            ),
        }


    def test_module_loader_unexisting(self):
        interpreter = dukpy.JSInterpreter()

        with self.assertRaises(JSRuntimeError) as err:
            interpreter.evaljs("require('missing_module');")
        assert "cannot find module: missing_module" in str(err.exception)
