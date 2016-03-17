from __future__ import unicode_literals
import json
import dukpy
from dukpy.webassets import BabelJS, TypeScript
from diffreport import report_diff

try:
    from io import StringIO
except:
    from StringIO import StringIO


class TestEvalJS(object):
    def test_filter_available(self):
        es6source = StringIO('''
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

        out = StringIO()
        BabelJS().input(es6source, out)
        
        out.seek(0)
        ans = out.read()

        assert '''var Point = (function () {
    function Point(x, y) {
''' in ans, ans
        
    def test_typescript_filter(self):
        typeScript_source = StringIO('''
class Greeter {
    constructor(public greeting: string) { }
    greet() {
        return "<h1>" + this.greeting + "</h1>";
    }
};
var greeter = new Greeter("Hello, world!");
''')
        out = StringIO()
        TypeScript().input(typeScript_source, out)
        
        out.seek(0)
        ans = out.read()
        
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
});
"""
        assert expected in ans, report_diff(expected, ans)
