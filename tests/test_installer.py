# -*- coding: utf-8 -*-
import os
import shutil
import tempfile

import sys
import mock
from nose import SkipTest
from nose.tools import raises

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
        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '0.14.8', self.tmpdir]):
            dukpy_install.main()
        assert os.path.exists(os.path.join(self.tmpdir, 'react'))

    def test_install_command_missing_args(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install']):
            assert dukpy_install.main() == 1

    def test_install_command_without_dest(self):
        if os.path.exists('./js_modules'):
            raise SkipTest('local destination directory already exists...')

        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '0.14.8']):
            dukpy_install.main()
        assert os.path.exists(os.path.join('./js_modules', 'react'))

    def test_install_command_substrate_error(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '9999', self.tmpdir]):
            assert dukpy_install.main() == 2

    def test_install_unexisting_package(self):
        try:
            dukpy.install_jspackage('non_existing_suerly_missing_dunno', '1', self.tmpdir)
        except:
            pass
        else:
            assert False, 'Should have not found exception'

    @raises(dukpy_install.JSPackageInstallError)
    def test_install_unexisting_version(self):
        dukpy.install_jspackage('react', '9999', self.tmpdir)

    @raises(dukpy_install.JSPackageInstallError)
    def test_install_missing_download_url(self):
        with mock.patch('json.loads', new=lambda *args: {'versions': {'9999': {}}}):
            try:
                dukpy.install_jspackage('react', '9999', self.tmpdir)
            except Exception as e:
                assert 'Unable to detect a supported download url' in str(e), str(e)
                raise


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
