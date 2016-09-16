# -*- coding: utf-8 -*-
import os
from unittest import TestCase

import dukpy
from diffreport import report_diff
from dukpy.lessc import LessCompilerError


class TestTranspilers(TestCase):
    def test_coffee(self):
        ans = dukpy.coffee_compile('''
    fill = (container, liquid = "coffee") ->
        "Filling the #{container} with #{liquid}..."
''')
        assert ans == '''(function() {
  var fill;

  fill = function(container, liquid) {
    if (liquid == null) {
      liquid = "coffee";
    }
    return "Filling the " + container + " with " + liquid + "...";
  };

}).call(this);
'''

    def test_babel(self):
        ans = dukpy.babel_compile('''
class Point {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }
    toString() {
        return '(' + this.x + ', ' + this.y + ')';
    }
}
''')
        assert '''var Point = function () {
    function Point(x, y) {
''' in ans['code'], ans['code']

    def test_typescript(self):
        ans = dukpy.typescript_compile('''
class Greeter {
    constructor(public greeting: string) { }
    greet() {
        return "<h1>" + this.greeting + "</h1>";
    }
};

var greeter = new Greeter("Hello, world!");
''')

        expected = """System.register([], function(exports_1) {
    var Greeter, greeter;
    return {
        setters:[],
        execute: function() {
            var Greeter = (function () {
                function Greeter(greeting) {
                    this.greeting = greeting;
                }
                Greeter.prototype.greet = function () {
                    return "<h1>" + this.greeting + "</h1>";
                };
                return Greeter;
            })();
            ;
            var greeter = new Greeter("Hello, world!");
        }
    }
});"""

        assert expected in ans, report_diff(expected, ans)

    def test_jsx(self):
        ans = dukpy.jsx_compile('var react_hello = <h1>Hello, world!</h1>;')

        expected = """"use strict";

var react_hello = React.createElement(\n  "h1",\n  null,\n  "Hello, world!"\n);"""

        assert expected == ans, report_diff(expected, ans)

    def test_jsx6(self):
        ans = dukpy.jsx_compile('''
import Component from 'react';

class HelloWorld extends Component {
  render() {
    return (
      <div className="helloworld">
        Hello {this.props.data.name}
      </div>
    );
  }
}
''')
        assert '_createClass(HelloWorld,' in ans, ans

    def test_less(self):
        ans = dukpy.less_compile('''
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
''', options={'paths': [os.path.dirname(__file__)]})

        expected = '''box {
  color: #7cb029;
  border-color: #c2e191;
}
.box div {
  -webkit-box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
}'''

        assert expected in ans, report_diff(expected, ans)

    def test_less_errors(self):
        try:
            dukpy.less_compile('@import "files/missing.less";')
        except LessCompilerError as e:
            assert "files/missing.less' wasn't found." in str(e)
        else:
            assert False, 'Exception not raised'