# -*- coding: utf-8 -*-
import dukpy
from diffreport import report_diff


class TestTranspilers(object):
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
        assert '''var Point = (function () {
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