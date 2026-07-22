from __future__ import unicode_literals

import re

import dukpy
import dukpy.webassets
from dukpy.webassets import TypeScript, CompileLess, BabelJSX
from webassets.test import TempEnvironmentHelper


class PyTestTempEnvironmentHelper(TempEnvironmentHelper):
    """Adapt TempEnvironmentHelper to be compatible with PyTest"""

    def setup_method(self, method=None):
        parent = super(PyTestTempEnvironmentHelper, self)
        if hasattr(parent, "setup_method"):
            parent.setup_method()
        elif hasattr(parent, "setup"):
            parent.setup()

    def teardown_method(self, method=None):
        parent = super(PyTestTempEnvironmentHelper, self)
        if hasattr(parent, "teardown_method"):
            parent.teardown_method()
        elif hasattr(parent, "teardown"):
            parent.teardown()


class TestAssetsFilters(PyTestTempEnvironmentHelper):
    def test_generic_babel_filter_is_not_public(self):
        assert not hasattr(dukpy.webassets, "BabelJS")

    @classmethod
    def setup_class(cls):
        from webassets.filter import register_filter

        register_filter(TypeScript)

    def test_typescript_filter(self):
        typeScript_source = """
class Greeter {
    constructor(public greeting: string) { }
    greet() {
        return "<h1>" + this.greeting + "</h1>";
    }
};
globalThis.typescript_result = new Greeter("Hello, world!").greet();
"""

        self.create_files({"in": typeScript_source})
        self.mkbundle("in", filters="typescript", output="out").build()
        ans = self.get("out")

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


class TestLessFilter(PyTestTempEnvironmentHelper):
    LESS_CODE = """
@import "colors.less";
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
}"""

    @classmethod
    def setup_class(cls):
        from webassets.filter import register_filter

        register_filter(CompileLess)

    def test_less_with_imports(self):
        self.create_files({"in": self.LESS_CODE, "colors.less": "@green: #7bab2e;"})
        self.mkbundle("in", filters="lessc", output="out").build()
        ans = self.get("out")
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


class TestJSXFilter(PyTestTempEnvironmentHelper):
    JSX_CODE = """
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
globalThis.jsx_filter_result = ReactDOM.renderToStaticMarkup(
  <HelloWorld data={{name: 'Ada'}}/>, null
);
"""

    @classmethod
    def setup_class(cls):
        from webassets.filter import register_filter

        register_filter(BabelJSX)

    def test_jsx(self):
        self.create_files({"in": self.JSX_CODE})
        self.mkbundle("in", filters="babeljsx", output="out").build()
        assert dukpy.evaljs([self.get("out"), "globalThis.jsx_filter_result"]) == (
            '<div class="helloworld">Hello Ada</div>'
        )

    def test_jsx_options(self):
        self.create_files({"in": self.JSX_CODE})
        self.mkbundle(
            "in",
            filters="babeljsx",
            output="out",
            config={"babel_modules_loader": "systemjs"},
        ).build()
        ans = self.get("out")
        assert dukpy.evaljs(
            [
                """
var system_dependencies = [];
var System = {
    register: function(deps, factory) {
        system_dependencies = deps;
        var module = factory(function(){});
        module.setters[0]({default: require('react/react')});
        module.execute();
    }
};
""",
                ans,
                "({deps: system_dependencies, html: globalThis.jsx_filter_result})",
            ]
        ) == {
            "deps": ["react/react"],
            "html": '<div class="helloworld">Hello Ada</div>',
        }

    def test_jsx_umd_option(self):
        self.create_files({"in": self.JSX_CODE})
        self.mkbundle(
            "in",
            filters="babeljsx",
            output="out",
            config={"babel_modules_loader": "umd"},
        ).build()
        interpreter = dukpy.JSInterpreter()

        assert (
            interpreter.evaljs(
                [
                    """
var react = require('react/react'),
    reactDomServer = require('react/react-dom-server');
""",
                    self.get("out"),
                    "globalThis.jsx_filter_result",
                ]
            )
            == '<div class="helloworld">Hello Ada</div>'
        )
