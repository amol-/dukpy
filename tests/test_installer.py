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

        jsx = dukpy.jsx_compile(TEST_CODE)

        jsi = dukpy.JSInterpreter()
        jsi.loader.register_path(self.tmpdir)
        res = jsi.evaljs(jsx, data={'id': 1, 'name': "Alessandro"})
        assert res == '<div class="helloworld">Hello Alessandro</div>', res

    def test_install_command(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '0.14.8',
                                             '-d', self.tmpdir]):
            dukpy_install.main()
        assert os.path.exists(os.path.join(self.tmpdir, 'react'))

    def test_install_command_latest_ver(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '-d', self.tmpdir]):
            dukpy_install.main()
        assert os.path.exists(os.path.join(self.tmpdir, 'react'))

    @raises(SystemExit)
    def test_install_command_missing_args(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install']):
            dukpy_install.main()

    def test_install_command_without_dest(self):
        if os.path.exists('./js_modules'):
            raise SkipTest('local destination directory already exists...')

        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '0.14.8']):
            dukpy_install.main()
        assert os.path.exists(os.path.join('./js_modules', 'react'))

    def test_install_scoped_package(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install', '@reactivex/rxjs', '5.0.0-beta.11']):
            dukpy_install.main()
        assert os.path.exists(os.path.join('./js_modules', '@reactivex', 'rxjs'))

    def test_install_command_substrate_error(self):
        with mock.patch.object(sys, 'argv', ['dukpy-install', 'react', '9999',
                                             '-d', self.tmpdir]):
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
        with mock.patch('dukpy.install._fetch_package_info',
                        new=lambda *args: {'versions': {'99.9.9': {}}}):
            try:
                dukpy.install_jspackage('react', '99.9.9', self.tmpdir)
            except Exception as e:
                assert 'Unable to detect a supported download url' in str(e), str(e)
                raise


class TestVersionResolver(object):
    VERSIONS = {"0.14.5": {}, "0.13.0-rc2": {}, "0.13.0-rc1": {}, "0.14.0-beta3": {}, "0.2.6": {},
                "0.2.5": {}, "0.2.4": {}, "0.2.3": {}, "0.2.2": {}, "0.2.1": {}, "0.2.0": {},
                "0.1.2": {}, "0.3.5": {}, "0.10.0-rc1": {}, "0.14.0": {}, "0.10.0": {},
                "0.13.0-beta.2": {}, "0.0.1": {}, "0.14.3": {}, "0.0.3": {}, "0.0.2": {},
                "0.6.3": {}, "0.6.2": {}, "0.3.0": {}, "0.6.0": {}, "0.11.0": {}, "0.11.1": {},
                "0.3.4": {}, "0.7.1": {}, "15.0.0": {}, "15.0.1": {}, "0.12.1": {}, "0.12.0": {},
                "0.15.0-alpha.1": {}, "0.5.1": {}, "0.5.0": {}, "0.13.3": {}, "0.5.2": {},
                "0.13.1": {}, "0.14.0-beta2": {}, "0.14.4": {}, "0.14.7": {}, "0.14.0-beta1": {},
                "0.14.1": {}, "15.0.0-rc.2": {}, "15.0.0-rc.1": {}, "0.14.2": {}, "0.14.8": {},
                "0.9.0": {}, "0.8.0": {}, "0.14.0-rc1": {}, "0.12.0-rc1": {}, "0.6.1": {},
                "0.12.2": {}, "0.11.2": {}, "0.9.0-rc1": {}, "0.13.2": {}, "0.14.0-alpha2": {},
                "0.14.0-alpha1": {}, "0.14.0-alpha3": {}, "0.13.0-beta.1": {}, "0.13.0-alpha.2": {},
                "0.13.0-alpha.1": {}, "0.13.0": {}, "0.7.0": {}, "0.14.6": {}, "0.11.0-rc1": {}}

    def test_tilde_versioning(self):
        ver = dukpy_install._resolve_version('~0.14.x', self.VERSIONS)
        assert ver == '0.14.8', ver

    def test_caret_versioning(self):
        ver = dukpy_install._resolve_version('^0.x', self.VERSIONS)
        assert ver == '0.14.8', ver

    def test_equality(self):
        ver = dukpy_install._resolve_version('0.2.4', self.VERSIONS)
        assert ver == '0.2.4', ver

    def test_last(self):
        ver = dukpy_install._resolve_version('', self.VERSIONS)
        assert ver == '15.0.1', ver


TEST_CODE = '''
var React = require('react'),
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
