# -*- coding: utf-8 -*-
import dukpy


class TestReactJS(object):
    def test_hello_world(self):
        jsx = dukpy.jsx_compile('var react_hello = <h1>Hello, world!</h1>;')
        jsi = dukpy.JSInterpreter()
        result = jsi.evaljs([
            '''
            var React = require('react/react'),
             ReactDOM = require('react/react-dom-server');
            ''',
            jsx,
            'ReactDOM.renderToStaticMarkup(react_hello, null);'
        ])
        assert result == '<h1>Hello, world!</h1>', res

    def test_jsx_mixed(self):
        code = '''
var React = require('react/react'),
 ReactDOM = require('react/react-dom-server');
ReactDOM.renderToStaticMarkup(<h1>Hello, world!</h1>, null);
'''
        jsx = dukpy.jsx_compile(code)
        res = dukpy.evaljs(jsx)
        assert res == '<h1>Hello, world!</h1>', res

    def test_react_binding(self):
        code = '''
var React = require('react/react'),
 ReactDOM = require('react/react-dom-server');

var HelloWorld = React.createClass({
  render: function() {
    return (
      <div className="helloworld">
        Hello {this.props.data.name}
      </div>
    );
  }
});

ReactDOM.renderToStaticMarkup(<HelloWorld data={dukpy.data}/>, null);
'''
        jsx = dukpy.jsx_compile(code)
        res = dukpy.evaljs(jsx, data={'id': 1, 'name': "Alessandro"})
        assert res == '<div class="helloworld">Hello Alessandro</div>', res

    def test_jsx6(self):
        code = '''
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
'''
        jsx = dukpy.jsx_compile(code)
        res = dukpy.evaljs(jsx, data={'id': 1, 'name': "Alessandro"})
        assert res == '<div class="helloworld">Hello Alessandro</div>', res
