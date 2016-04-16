# -*- coding: utf-8 -*-
import os
import shutil
import tempfile

import sys
import mock
import dukpy
from dukpy import install as dukpy_install


class TestPackageInstaller(object):
    def setup(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_install_react(self):
        dukpy.install_jspackage('react', '0.14.8', self.tmpdir)
        dukpy.install_jspackage('react-dom', '0.14.8', self.tmpdir)
        dukpy.install_jspackage('fbjs', '0.8.0', self.tmpdir)

        jsx = dukpy.jsx_compile(TEST_CODE)

        jsi = dukpy.JSInterpreter()
        jsi.loader.register_path(self.tmpdir)
        res = jsi.evaljs(jsx, data={'id': 1, 'name': "Alessandro"})
        assert res == '<div class="helloworld">Hello Alessandro</div>', res

    def test_install_command(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '0.14.8']):
            dukpy_install.main()
        assert os.path.exists(os.path.join('./js_modules', 'react'))


TEST_CODE = '''
var React = require('react/react'),
 ReactDOM = require('react-dom/server');

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
