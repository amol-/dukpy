from __future__ import unicode_literals

from dukpy.webassets import BabelJS, TypeScript, CompileLess, BabelJSX
from diffreport import report_diff
from webassets.test import TempEnvironmentHelper

try:
    from io import StringIO
except:
    from StringIO import StringIO


class TestAssetsFilters(TempEnvironmentHelper):
    @classmethod
    def setup_class(cls):
        from webassets.filter import register_filter
        register_filter(BabelJS)
        register_filter(TypeScript)

    def test_babeljs_filter(self):
        ES6CODE = '''
class Point {
    constructor(x, y) {
        this.x = x;
        this.y = y;
    }
    toString() {
        return '(' + this.x + ', ' + this.y + ')';
    }
}
'''
        self.create_files({'in': ES6CODE})
        self.mkbundle('in', filters='babeljs', output='out').build()
        ans = self.get('out')

        assert '''var Point = function () {
    function Point(x, y) {
''' in ans, ans
        
    def test_typescript_filter(self):
        typeScript_source = '''
class Greeter {
    constructor(public greeting: string) { }
    greet() {
        return "<h1>" + this.greeting + "</h1>";
    }
};
var greeter = new Greeter("Hello, world!");
'''

        self.create_files({'in': typeScript_source})
        self.mkbundle('in', filters='typescript', output='out').build()
        ans = self.get('out')

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


class TestLessFilter(TempEnvironmentHelper):
    LESS_CODE = '''
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
}'''

    @classmethod
    def setup_class(cls):
        from webassets.filter import register_filter
        register_filter(CompileLess)

    def test_less_with_imports(self):
        self.create_files({
            'in': self.LESS_CODE,
            'colors.less': '@green: #7bab2e;'
        })
        self.mkbundle('in', filters='lessc', output='out').build()
        assert self.get('out') == """.box {
  color: #7cb029;
  border-color: #c2e191;
}
.box div {
  -webkit-box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
  box-shadow: 0 0 5px rgba(0, 0, 0, 0.3);
}
"""


class TestJSXFilter(TempEnvironmentHelper):
    JSX_CODE = '''
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
'''

    @classmethod
    def setup_class(cls):
        from webassets.filter import register_filter
        register_filter(BabelJSX)

    def test_jsx(self):
        self.create_files({'in': self.JSX_CODE})
        self.mkbundle('in', filters='babeljsx', output='out').build()
        assert '_createClass(HelloWorld, ' in self.get('out')
        assert 'require' in self.get('out')

    def test_jsx_options(self):
        self.create_files({'in': self.JSX_CODE})
        self.mkbundle('in', filters='babeljsx', output='out', config={
            'babel_modules_loader': 'systemjs'
        }).build()
        assert 'System.register(["react"]' in self.get('out')