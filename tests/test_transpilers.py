# -*- coding: utf-8 -*-
import os
import re
import unittest

import dukpy
from dukpy.lessc import LessCompilerError


class TestTranspilers(unittest.TestCase):
    def test_coffee(self):
        ans = dukpy.coffee_compile("""
fill = (container, liquid = "coffee") ->
    "Filling the #{container} with #{liquid}..."
@coffee_result = [fill("cup"), fill("kettle", "tea")]
""")
        assert dukpy.evaljs([ans, "coffee_result"]) == [
            "Filling the cup with coffee...",
            "Filling the kettle with tea...",
        ]

    def test_babel(self):
        ans = dukpy.babel_compile("""
export function greet(name = "Ada") {
    return `Hello ${name}`;
}
globalThis.babel_result = greet();
""")
        assert (
            dukpy.evaljs(
                [
                    "var exports = {};",
                    ans["code"],
                    "exports.greet('Grace') + ' / ' + globalThis.babel_result",
                ]
            )
            == "Hello Grace / Hello Ada"
        )

    def test_typescript(self):
        ans = dukpy.typescript_compile("""
class Greeter {
    constructor(public greeting: string) { }
    greet() {
        return "<h1>" + this.greeting + "</h1>";
    }
};
globalThis.typescript_result = new Greeter("Hello, world!").greet();
""")

        assert (
            dukpy.evaljs(
                [
                    """
var System = {
    register: function(deps, factory) {
        var module = factory(function(){});
        module.execute();
    }
};
""",
                    ans,
                    "globalThis.typescript_result",
                ]
            )
            == "<h1>Hello, world!</h1>"
        )

    def test_jsx(self):
        ans = dukpy.jsx_compile("var react_hello = <h1>Hello, world!</h1>;")
        interpreter = dukpy.JSInterpreter()

        assert (
            interpreter.evaljs(
                [
                    """
var React = require('react/react'),
    ReactDOM = require('react/react-dom-server');
""",
                    ans,
                    "ReactDOM.renderToStaticMarkup(react_hello, null);",
                ]
            )
            == "<h1>Hello, world!</h1>"
        )

    def test_jsx6(self):
        ans = dukpy.jsx_compile("""
import React from 'react/react';
var ReactDOM = require('react/react-dom-server');

class HelloWorld extends React.Component {
  render() {
    return (
      <div className="helloworld">
        Hello {this.props.data.name}
      </div>
    );
  }
}

ReactDOM.renderToStaticMarkup(<HelloWorld data={dukpy.data}/>, null);
""")
        assert dukpy.evaljs(ans, data={"id": 1, "name": "Ada"}) == (
            '<div class="helloworld">Hello Ada</div>'
        )

    def test_less(self):
        ans = dukpy.less_compile(
            """
@import "files/colors.less";

.box-shadow(@style, @c) when (iscolor(@c)) {
  -webkit-box-shadow: @style @c;
  box-shadow:         @style @c;
}
.box-shadow(@style, @alpha: 50%) when (isnumber(@alpha)) {
  .box-shadow(@style, rgba(0, 0, 0, @alpha));
}
.box {
  color: saturate(@green, 5%);
  border-color: lighten(@green, 30%);
  div { .box-shadow(0 0 5px, 30%) }
}
""",
            options={"paths": [os.path.dirname(__file__)]},
        )

        assert re.search(r"\.box\s*\{[^}]*\bcolor\s*:\s*#7cb029\b", ans)
        assert re.search(r"\.box\s*\{[^}]*\bborder-color\s*:\s*#c2e191\b", ans)
        assert re.search(
            r"\.box\s+div\s*\{[^}]*-webkit-box-shadow\s*:\s*"
            r"0\s+0\s+5px\s+rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.3\s*\)",
            ans,
        )
        assert re.search(
            r"\.box\s+div\s*\{[^}]*(?<!-)box-shadow\s*:\s*"
            r"0\s+0\s+5px\s+rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\.3\s*\)",
            ans,
        )

    def test_less_errors(self):
        with self.assertRaises(LessCompilerError) as err:
            dukpy.less_compile('@import "files/missing.less";')
        assert "files/missing.less' wasn't found." in str(err.exception)
