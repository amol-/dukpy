# -*- coding: utf-8 -*-
from dukpy.nodelike import NodeLikeInterpreter


def test_node_like_core_shims_use_commonjs_require_and_python_fs_bridge(tmp_path):
    (tmp_path / "fixture.txt").write_text("hello snowman ☃", encoding="utf-8")

    result = NodeLikeInterpreter().evaljs(
        """
        var fs = require('fs');
        var path = require('path');
        var url = require('url');
        var querystring = require('querystring');
        var punycode = require('punycode');
        var parsed = url.parse(
            'https://mañana.example/search?q=hello%20world&q=again&snow=%E2%98%83',
            true
        );
        ({
            fileExists: !!fs.statSync(path.join(dukpy.base, 'fixture.txt')),
            fileContents: fs.readFileSync(
                path.join(dukpy.base, 'fixture.txt'), 'utf-8'
            ),
            basename: path.basename('/tmp/example.less'),
            dirname: path.dirname('/tmp/example.less'),
            extname: path.extname('/tmp/example.less'),
            relative: path.relative('/tmp/app/styles', '/tmp/app/images/logo.svg'),
            resolved: path.resolve('/tmp/app', '../pkg', './index.js'),
            parsedHost: parsed.host,
            parsedQueryQ: parsed.query.q,
            parsedSnow: parsed.query.snow,
            encoded: querystring.stringify({
                q: ['hello world', 'again'],
                snow: '☃'
            }),
            ascii: punycode.toASCII('mañana.example'),
            unicode: punycode.toUnicode('xn--maana-pta.example')
        });
        """,
        base=str(tmp_path),
    )

    assert result == {
        "fileExists": True,
        "fileContents": "hello snowman ☃",
        "basename": "example.less",
        "dirname": "/tmp",
        "extname": ".less",
        "relative": "../images/logo.svg",
        "resolved": "/tmp/pkg/index.js",
        "parsedHost": "xn--maana-pta.example",
        "parsedQueryQ": ["hello world", "again"],
        "parsedSnow": "☃",
        "encoded": "q=hello%20world&q=again&snow=%E2%98%83",
        "ascii": "xn--maana-pta.example",
        "unicode": "mañana.example",
    }


def test_node_like_runs_bundled_less_with_synchronous_render_callback(tmp_path):
    (tmp_path / "colors.less").write_text("@green: #6c9f20;\n", encoding="utf-8")

    result = NodeLikeInterpreter().evaljs(
        """
        var less = require('less/less-node');
        var events = [];
        var result = null;
        less.render(
            dukpy.source,
            {paths: [dukpy.base], syncImport: true},
            function(error, output) {
                events.push('callback');
                result = {
                    error: error && error.message,
                    css: output && output.css
                };
            }
        );
        events.push('after-render');
        result.events = events;
        result;
        """,
        source='@import "colors.less";\n.box { color: lighten(@green, 10%); }',
        base=str(tmp_path),
    )

    assert result == {
        "error": None,
        "css": ".box {\n  color: #89c929;\n}\n",
        "events": ["callback", "after-render"],
    }


def test_node_like_runs_bundled_react_commonjs_modules():
    result = NodeLikeInterpreter().evaljs(
        """
        var React = require('react/react');
        var ReactDOM = require('react/react-dom-server');
        ReactDOM.renderToStaticMarkup(
            React.createElement('span', {className: 'greet'}, 'Hello ', dukpy.name)
        );
        """,
        name="QuickJS",
    )

    assert result == '<span class="greet">Hello QuickJS</span>'
