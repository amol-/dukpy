# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import importlib
import io
import logging
import multiprocessing
import os
import signal

import dukpy

try:
    import mock
except ImportError:
    from unittest import mock

import pytest


# Eval basics


def test_evaljs_evaluates_modern_javascript_syntax_smoke():
    assert (
        dukpy.evaljs(
            "(() => { const value = {nested: {answer: 42}}; return value?.nested?.answer ?? 0; })()"
        )
        == 42
    )


def test_evaljs_returns_object_from_multiple_source_fragments():
    ans = dukpy.evaljs(["var o = {'value': 5}", "o['value'] += 3", "o"])
    assert ans == {"value": 8}


def test_public_javascript_api_is_evaljs_and_run_only():
    evaljs_module = importlib.import_module("dukpy.evaljs")

    assert not hasattr(dukpy, "evaljs_module")
    assert not hasattr(dukpy.JSInterpreter(), "evaljs_module")
    assert not hasattr(evaljs_module, "evaljs_module")


# Host globals


def test_evaljs_exposes_keyword_arguments_on_dukpy_global():
    n = dukpy.evaljs("dukpy['value'] + 3", value=7)
    assert n == 10


def test_evaljs_preserves_unicode_keyword_values():
    s = dukpy.evaljs("dukpy.c + 'A'", c="華")
    assert s == "華A"


def test_evaljs_preserves_unicode_source_text():
    s = dukpy.evaljs("dukpy.c + '華'", c="華")
    assert s == "華華"


def test_evaljs_preserves_emoji_keyword_values():
    s1 = dukpy.evaljs("dukpy.c + 'B'", c="🏠")
    assert s1 == "🏠B"

    s2 = dukpy.evaljs("dukpy.c + 'C'", c="👍🏾")
    assert s2 == "👍🏾C"

    s3 = dukpy.evaljs("dukpy.c + '華'", c="🏠")
    assert s3 == "🏠華"


def test_evaljs_keeps_kwargs_as_user_data_when_module_api_exists():
    assert (
        dukpy.evaljs(
            "dukpy.eval_as_module + dukpy.evaljs_module + dukpy.module + dukpy.module_name",
            eval_as_module=20,
            evaljs_module=20,
            module=1,
            module_name=1,
        )
        == 42
    )


def test_evaljs_does_not_expose_static_import_module_support():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs("import './dep.mjs';")

    assert "SyntaxError:" in str(exc.value)


@pytest.mark.parametrize(
    ("method", "logger_method"),
    (("log", "info"), ("info", "info"), ("warn", "warn"), ("error", "error")),
)
def test_console_methods_log_user_arguments(method, logger_method):
    log = logging.getLogger("dukpy.interpreter")

    with mock.patch.object(log, logger_method, return_value=None) as fakelog:
        assert dukpy.evaljs(f"console.{method}('HI', 3, true); 42") == 42

    fakelog.assert_called_once_with("HI 3 true")


def test_process_env_exposes_environment_snapshot():
    with mock.patch.dict(os.environ, {"DUKPY_EVO_090_ENV": "compat-value"}):
        interpreter = dukpy.JSInterpreter()

    assert interpreter.evaljs(
        """
        ({
            hasProcessObject: typeof process === 'object',
            hasEnvObject: typeof process.env === 'object',
            envValue: process.env.DUKPY_EVO_090_ENV
        });
        """
    ) == {
        "hasProcessObject": True,
        "hasEnvObject": True,
        "envValue": "compat-value",
    }


# Callback bridge


def _assert_callback_exception_marshalling_is_safe():
    interpreter = dukpy.JSInterpreter()

    class BrokenRepr(Exception):
        def __repr__(self):
            raise RuntimeError("repr failed")

    def fail_broken_repr():
        raise BrokenRepr("boom")

    def fail_null_error_value():
        import ctypes

        pyerr_setnone = ctypes.pythonapi.PyErr_SetNone
        pyerr_setnone.argtypes = [ctypes.py_object]
        pyerr_setnone.restype = None
        pyerr_setnone(RuntimeError)

    interpreter.export_function("fail_broken_repr", fail_broken_repr)
    interpreter.export_function("fail_null_error_value", fail_null_error_value)

    for func_name in ("fail_broken_repr", "fail_null_error_value"):
        result = interpreter.evaljs(
            """
            var caught = null;
            try {
                call_python(dukpy.func_name);
            } catch (e) {
                caught = {name: e.name, message: e.message};
            }
            caught;
            """,
            func_name=func_name,
        )
        assert result["name"] == "InternalError"
        assert result["message"].startswith(
            f"Error while calling Python Function ({func_name}): "
        )

    assert interpreter.evaljs("40 + 2") == 42


def test_call_python_receives_emoji_arguments_from_javascript():
    dukpy.evaljs("call_python('dukpy.log.info', dukpy.c, '🏠')", c="🏠")

    s3 = dukpy.evaljs("dukpy.c + '🏠'", c="🏠")
    assert s3 == "🏠🏠"


def test_call_python_lookup_failure_is_catchable_js_exception():
    interpreter = dukpy.JSInterpreter()

    assert (
        interpreter.evaljs(
            """
            var caught = false;
            try {
                call_python('☃');
            } catch (e) {
                caught = e.name === 'ReferenceError' &&
                         e.message === 'No Python Function named ☃';
            }
            caught ? 42 : 0;
            """
        )
        == 42
    )


def test_call_python_callback_exception_is_catchable_internal_error():
    interpreter = dukpy.JSInterpreter()

    def fail():
        raise ValueError("boom")

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
        "message": "Error while calling Python Function (fail): ValueError('boom')",
    }


def test_call_python_callback_exception_marshalling_is_safe_for_unusual_errors():
    _assert_callback_exception_marshalling_is_safe()


# JSON conversion


@pytest.mark.parametrize(
    ("code", "expected"),
    (
        ("null", None),
        ("undefined", None),
        ("NaN", None),
        ("Infinity", None),
        ("-Infinity", None),
        ("new Error('boom')", {}),
        ("/abc/gi", {}),
        ("new Map([['answer', 42]])", {}),
        ("new Set([1, 2])", {}),
        (
            "[undefined, function(){}, Symbol('x'), NaN, Infinity]",
            [None, None, None, None, None],
        ),
        (
            "({keep: 1, missing: undefined, fn: function(){}, sym: Symbol('x'), nan: NaN, inf: Infinity})",
            {"keep": 1, "nan": None, "inf": None},
        ),
    ),
)
def test_evaljs_result_conversion_follows_json_stringify_contract(code, expected):
    assert dukpy.evaljs(code) == expected


@pytest.mark.parametrize("code", ("(function(){})", "Symbol('x')"))
def test_evaljs_rejects_top_level_values_json_stringify_cannot_emit(code):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(code)
    assert str(exc.value) == "Invalid Result Value"


@pytest.mark.parametrize(
    ("code", "expected_message"),
    (
        ("1n", "TypeError: BigInt are forbidden in JSON.stringify"),
        ("[1n]", "TypeError: BigInt are forbidden in JSON.stringify"),
        ("var value = {}; value.self = value; value", "TypeError: circular reference"),
        ("var value = []; value[0] = value; value", "TypeError: circular reference"),
    ),
)
def test_evaljs_reports_json_stringify_conversion_failures(code, expected_message):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(code)
    assert expected_message in str(exc.value)


# Promise/job draining


def test_evaljs_drains_promise_microtasks_before_serializing_result():
    assert dukpy.evaljs(
        """
        var result = {value: 1};
        Promise.resolve().then(function() { result.value = 2; });
        result;
        """
    ) == {"value": 2}


def test_evaljs_propagates_pending_promise_job_failures():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            """
            Promise.resolve().then(function() {
                throw new Error('microtask failed');
            });
            ({ok: true});
            """
        )
    assert "Error: microtask failed" in str(exc.value)


def test_evaljs_drains_promise_microtasks_created_by_to_json():
    interpreter = dukpy.JSInterpreter()

    assert (
        interpreter.evaljs(
            """
        var state = {serialized: false};
        ({
            toJSON: function() {
                Promise.resolve().then(function() { state.serialized = true; });
                return 'serialized';
            }
        });
        """
        )
        == "serialized"
    )
    assert interpreter.evaljs("state.serialized") is True


def test_evaljs_reports_to_json_unhandled_rejections_in_current_eval():
    interpreter = dukpy.JSInterpreter()

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs(
            """
            ({
                toJSON: function() {
                    Promise.reject(new Error('serialization rejection'));
                    return {ok: true};
                }
            });
            """
        )
    assert "Error: serialization rejection" in str(exc.value)
    assert interpreter.evaljs("40 + 2") == 42


def test_evaljs_does_not_leak_to_json_jobs_when_serialization_throws():
    interpreter = dukpy.JSInterpreter()

    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs(
            """
            ({
                toJSON: function() {
                    Promise.reject(new Error('discarded serialization rejection'));
                    Promise.resolve().then(function() {
                        throw new Error('discarded serialization job');
                    });
                    throw new Error('serialization failed');
                }
            });
            """
        )
    assert "Error: serialization failed" in str(exc.value)
    assert interpreter.evaljs("40 + 2") == 42


def test_evaljs_rejects_reentrant_eval_while_promise_jobs_are_draining():
    interpreter = dukpy.JSInterpreter()
    nested_error = None

    def nested_eval():
        nonlocal nested_error
        try:
            interpreter.evaljs(
                """
                globalThis.nestedJobLeaked = false;
                Promise.resolve().then(function() {
                    globalThis.nestedJobLeaked = true;
                });
                ({value: globalThis.nestedJobLeaked});
                """
            )
        except dukpy.JSRuntimeError as exc:
            nested_error = str(exc)
            return nested_error
        raise AssertionError("reentrant evaljs from a Promise job should fail")

    interpreter.export_function("nested_eval", nested_eval)

    assert interpreter.evaljs(
        """
        globalThis.outerMicrotaskRan = false;
        Promise.resolve().then(function() {
            globalThis.nestedEvalError = call_python('nested_eval');
            globalThis.outerMicrotaskRan = true;
        });
        ({ok: true});
        """
    ) == {"ok": True}
    assert nested_error == "Cannot call evaljs while QuickJS Promise jobs are draining"
    assert interpreter.evaljs("globalThis.outerMicrotaskRan") is True
    assert interpreter.evaljs("typeof globalThis.nestedJobLeaked") == "undefined"
    assert interpreter.evaljs("40 + 2") == 42


def test_evaljs_reentrant_eval_outside_promise_job_draining_still_works():
    interpreter = dukpy.JSInterpreter()

    def nested_eval():
        return interpreter.evaljs(
            """
            var result = {value: 1};
            Promise.resolve().then(function() {
                result.value = 42;
                globalThis.normalNestedJobDrained = true;
            });
            result;
            """
        )

    interpreter.export_function("nested_eval", nested_eval)

    assert interpreter.evaljs("call_python('nested_eval')") == {"value": 42}
    assert interpreter.evaljs("globalThis.normalNestedJobDrained") is True


def test_evaljs_reentrant_eval_rejection_does_not_consume_outer_pending_rejection():
    interpreter = dukpy.JSInterpreter()
    nested_error = None

    def nested_eval():
        nonlocal nested_error
        try:
            interpreter.evaljs("1 + 1")
        except dukpy.JSRuntimeError as exc:
            nested_error = str(exc)
            return None
        raise AssertionError("reentrant evaljs from a Promise job should fail")

    interpreter.export_function("nested_eval", nested_eval)
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter.evaljs(
            """
            Promise.reject(new Error('outer rejection'));
            Promise.resolve().then(function() {
                call_python('nested_eval');
            });
            ({ok: true});
            """
        )
    assert nested_error == "Cannot call evaljs while QuickJS Promise jobs are draining"
    assert "Error: outer rejection" in str(exc.value)
    assert "Error while calling Python Function" not in str(exc.value)


# JavaScript error reporting


@pytest.mark.parametrize(
    ("code", "first_line", "stack_markers"),
    (
        (
            "throw new Error('boom')",
            "Error: boom",
            ("    at <eval> (<dukpy>:",),
        ),
        (
            "function f(){ throw new Error('boom'); } function g(){ f(); } g();",
            "Error: boom",
            ("    at f (<dukpy>:", "    at g (<dukpy>:", "    at <eval> (<dukpy>:"),
        ),
        (
            "missingName + 1",
            "ReferenceError: missingName is not defined",
            ("    at <eval> (<dukpy>:",),
        ),
        (
            "雪 + 1",
            "ReferenceError: 雪 is not defined",
            ("    at <eval> (<dukpy>:",),
        ),
        (
            "null.f()",
            "TypeError: cannot read property 'f' of null",
            ("    at <eval> (<dukpy>:",),
        ),
    ),
)
def test_js_runtime_error_uses_quickjs_error_text_and_stack_frames(
    code, first_line, stack_markers
):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(code)

    message = str(exc.value)
    assert message.splitlines()[0] == first_line
    for marker in stack_markers:
        assert marker in message


@pytest.mark.parametrize(
    ("code", "stack_markers"),
    (
        (
            "eval(\"throw new Error('boom')\")",
            ("    at <eval> (<input>:", "    at <eval> (<dukpy>:"),
        ),
        (
            "new Function(\"throw new Error('boom')\")()",
            ("    at anonymous (<input>:", "    at <eval> (<dukpy>:"),
        ),
    ),
)
def test_js_runtime_error_preserves_quickjs_dynamic_input_stack_frames(
    code, stack_markers
):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(code)

    message = str(exc.value)
    assert message.splitlines()[0] == "Error: boom"
    for marker in stack_markers:
        assert marker in message


@pytest.mark.parametrize(
    ("stack", "expected"),
    (
        (
            "custom stack",
            "Error: boom\ncustom stack",
        ),
        (
            "    at <eval> (<dukpy>:1)",
            "Error: boom\n    at <eval> (<dukpy>:1)",
        ),
        (
            "    at x (<dukpy>:123:4)\n",
            "Error: boom\n    at x (<dukpy>:123:4)\n",
        ),
        (
            "    at <eval> (<dukpy>:1)\nx",
            "Error: boom\n    at <eval> (<dukpy>:1)\nx",
        ),
        (
            "    at <eval> (<input>:x)",
            "Error: boom\n    at <eval> (<input>:x)",
        ),
    ),
)
def test_js_runtime_error_preserves_custom_stack_text(stack, expected):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            """
            var error = new Error('boom');
            error.stack = dukpy.stack;
            throw error;
            """,
            stack=stack,
        )
    assert str(exc.value) == expected


def test_js_runtime_error_ignores_accessor_stack_returning_string():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            """
            var error = new Error('boom');
            Object.defineProperty(error, 'stack', {
                get: function() {
                    this.message = 'mutated by stack getter';
                    return 'getter stack';
                }
            });
            throw error;
            """
        )
    assert str(exc.value) == "Error: boom"


def test_js_runtime_error_ignores_accessor_stack_that_throws():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            """
            var error = new Error('boom');
            Object.defineProperty(error, 'stack', {
                get: function() {
                    this.message = 'mutated by stack getter';
                    throw new Error('stack getter ran');
                }
            });
            throw error;
            """
        )
    assert str(exc.value) == "Error: boom"


@pytest.mark.parametrize(
    "stack_expression",
    (
        "123",
        "null",
        "({toString: function() { "
        "error.message = 'mutated by stack toString'; "
        "throw new Error('stack toString ran'); }})",
    ),
)
def test_js_runtime_error_ignores_non_string_stack_values(stack_expression):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            f"""
            var error = new Error('boom');
            error.stack = {stack_expression};
            throw error;
            """
        )
    assert str(exc.value) == "Error: boom"


def test_js_runtime_error_ignores_proxy_stack_descriptor_trap():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            """
            var target = new Error('boom');
            var error = new Proxy(target, {
                getOwnPropertyDescriptor: function(target, property) {
                    if (property === 'stack') {
                        target.message = 'mutated by stack descriptor';
                        return {value: 'proxy stack', configurable: true};
                    }
                    return Reflect.getOwnPropertyDescriptor(target, property);
                }
            });
            throw error;
            """
        )
    assert "proxy stack" not in str(exc.value)
    assert "mutated by stack descriptor" not in str(exc.value)


def test_js_runtime_error_keeps_error_stack_boundary_out_of_user_objects():
    assert dukpy.evaljs(
        """
        var error = new Error('boom');
        ({
            prepareType: typeof Error.prepareStackTrace,
            hasNativeStackMarker: Object.prototype.hasOwnProperty.call(
                error, '__dukpy_native_stack__'
            )
        });
        """
    ) == {"prepareType": "undefined", "hasNativeStackMarker": False}


def test_js_runtime_error_preserves_function_names_that_look_like_host_locations():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(
            """
            var f = function(){ throw new Error('boom'); };
            Object.defineProperty(f, 'name', {value: 'x (<dukpy>:123)'});
            f();
            """
        )
    assert "    at x (<dukpy>:123) (<dukpy>:" in str(exc.value)
    assert "eval:123" not in str(exc.value)


def test_internal_evaljs_module_reports_import_failures_without_source_scanning():
    interpreter = dukpy.JSInterpreter()
    # Private module evaluation is intentional: this pins the native loader
    # boundary for a synthetic module id without involving filesystem metadata.
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        interpreter._evaljs_module(
            "import value from './missing-雪.js';",
            module_name="pkg/entry☃.mjs",
        )
    assert str(exc.value) == "ReferenceError: cannot find module: pkg/missing-雪.js"


# Runtime safety


def _quickjs_signal_exception_child():
    def raise_keyboard_interrupt(signum, frame):
        raise KeyboardInterrupt

    previous_handler = signal.signal(signal.SIGALRM, raise_keyboard_interrupt)
    signal.setitimer(signal.ITIMER_REAL, 0.1)
    try:
        dukpy.evaljs("while (true) {}")
    except KeyboardInterrupt:
        return
    except dukpy.JSRuntimeError as exc:
        raise AssertionError(f"expected KeyboardInterrupt, got JSRuntimeError: {exc}")
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
    raise AssertionError("expected KeyboardInterrupt")


def test_quickjs_runtime_rejects_oversized_allocations():
    with pytest.raises(dukpy.JSRuntimeError, match="out of memory"):
        dukpy.evaljs("new ArrayBuffer(192 * 1024 * 1024).byteLength")


def test_quickjs_runtime_rejects_stack_exhaustion():
    with pytest.raises(dukpy.JSRuntimeError, match="Maximum call stack size exceeded"):
        dukpy.evaljs("function f(){ return 1 + f(); } f();")


def test_quickjs_runtime_propagates_python_signal_exceptions():
    if not hasattr(signal, "setitimer"):
        pytest.skip("setitimer is unavailable on this platform")

    process_context = multiprocessing.get_context("spawn")
    process = process_context.Process(target=_quickjs_signal_exception_child)
    process.start()
    process.join(8)
    if process.is_alive():
        process.terminate()
        process.join(1)
        if process.is_alive():
            process.kill()
            process.join()
        raise AssertionError("QuickJS signal propagation scenario timed out")
    assert process.exitcode == 0


def test_quickjs_runtime_disables_blocking_atomics_wait():
    assert (
        dukpy.evaljs(
            """
            try {
                Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 1);
            } catch(e) {
                e.name + ': ' + e.message;
            }
            """
        )
        == "TypeError: cannot block in this thread"
    )


# Legacy source adaptation


def test_evaljs_accepts_file_like_source():
    testfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test.js")
    with open(testfile) as f:
        s = dukpy.evaljs(f)
    assert s == 8, s


def test_evaljs_file_like_source_remains_script_text():
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        dukpy.evaljs(io.StringIO("export const value = 42;"))

    assert "SyntaxError:" in str(exc.value)


def test_evaljs_accepts_multiple_file_like_sources():
    testfile = os.path.join(os.path.abspath(os.path.dirname(__file__)), "test.js")
    with open(testfile) as f:
        with open(testfile) as f2:
            s = dukpy.evaljs([f, f2])
    assert s == 11, s


def test_jsinterpreter_legacy_source_adaptation_contract():
    interpreter = dukpy.JSInterpreter()

    assert (
        interpreter.evaljs(
            io.StringIO(
                "var text = 'semicolon; and // comment text';\n"
                "// syntax-looking text import/export/await stays a comment\n"
                "text.indexOf(';') + 28;\n"
            )
        )
        == 37
    )
    assert (
        interpreter.evaljs(
            (
                io.StringIO(
                    "var text = 'not a boundary; // still string';\n"
                    "// trailing comments and newlines are preserved\n"
                ),
                "var value = 41\n",
                "(function(){ value += text.indexOf(';') === 14 ? 1 : 100; })()\n",
                "value",
            )
        )
        == 42
    )
