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
        assert result == '<h1>Hello, world!</h1>'
