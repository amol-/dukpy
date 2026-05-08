# -*- coding: utf-8 -*-
import logging
import sys

import pytest

import dukpy
import dukpy.run


def run_cli_script(monkeypatch, tmp_path, source):
    script = tmp_path / "script.js"
    script.write_text(source, encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["dukpy", str(script)])
    return dukpy.run.main()


def test_run_main_executes_plain_script_through_node_like_interpreter(
    monkeypatch, tmp_path, caplog
):
    caplog.set_level(logging.INFO, logger="dukpy.interpreter")

    run_cli_script(monkeypatch, tmp_path, "console.log('plain script');\n")

    assert "plain script" in caplog.messages


def test_run_main_adapts_leading_shebang_without_scanning_javascript(
    monkeypatch, tmp_path, caplog
):
    caplog.set_level(logging.INFO, logger="dukpy.interpreter")

    run_cli_script(
        monkeypatch,
        tmp_path,
        "#!/usr/bin/env dukpy\nconsole.log('hello ☃');\n",
    )

    assert "hello ☃" in caplog.messages


def test_run_main_shebang_adaptation_preserves_syntax_error_line_numbers(
    monkeypatch, tmp_path
):
    with pytest.raises(dukpy.JSRuntimeError) as exc:
        run_cli_script(
            monkeypatch,
            tmp_path,
            "#!/usr/bin/env dukpy\nvar ok = 1;\nvar = ;\n",
        )

    assert "<dukpy>:3" in str(exc.value)
