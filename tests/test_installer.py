# -*- coding: utf-8 -*-
import json
import os
import shutil
import sys
import tarfile
import tempfile
import unittest
from io import BytesIO
from unittest import mock

import dukpy
from dukpy import install as dukpy_install


class TestPackageInstaller(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_install_package_from_offline_registry_and_require_it(self):
        with self._patch_npm(self._offline_registry(), self._offline_tarballs()):
            dukpy.install_jspackage("offline-package", "1.0.0", self.tmpdir)

        jsi = dukpy.JSInterpreter()
        jsi.loader.register_path(self.tmpdir)
        assert jsi.evaljs("require('offline-package').answer") == 42

    def test_install_command(self):
        with self._patch_npm(self._offline_registry(), self._offline_tarballs()):
            with mock.patch.object(
                sys,
                "argv",
                ["dukpy-install", "offline-package", "1.0.0", "-d", self.tmpdir],
            ):
                dukpy_install.main()
        assert os.path.exists(os.path.join(self.tmpdir, "offline-package"))

    def test_install_command_latest_ver(self):
        with self._patch_npm(self._offline_registry(), self._offline_tarballs()):
            with mock.patch.object(
                sys, "argv", ["dukpy-install", "offline-package", "-d", self.tmpdir]
            ):
                dukpy_install.main()
        assert os.path.exists(os.path.join(self.tmpdir, "offline-package"))

    def test_install_command_missing_args(self):
        with self.assertRaises(SystemExit):
            with mock.patch.object(sys, "argv", ["dukpy-install"]):
                dukpy_install.main()

    def test_install_command_without_dest(self):
        cwd = os.getcwd()
        try:
            os.chdir(self.tmpdir)
            with self._patch_npm(self._offline_registry(), self._offline_tarballs()):
                with mock.patch.object(
                    sys, "argv", ["dukpy-install", "offline-package", "1.0.0"]
                ):
                    dukpy_install.main()
            assert os.path.exists(
                os.path.join(self.tmpdir, "js_modules", "offline-package")
            )
        finally:
            os.chdir(cwd)

    def test_install_scoped_package(self):
        with self._patch_npm(self._scoped_registry(), self._scoped_tarballs()):
            with mock.patch.object(
                sys,
                "argv",
                ["dukpy-install", "@fixture/scoped", "1.0.0", "-d", self.tmpdir],
            ):
                dukpy_install.main()
        assert os.path.exists(os.path.join(self.tmpdir, "@fixture", "scoped"))

    def test_install_command_substrate_error(self):
        with self._patch_npm(self._offline_registry(), self._offline_tarballs()):
            with mock.patch.object(
                sys,
                "argv",
                ["dukpy-install", "offline-package", "9999", "-d", self.tmpdir],
            ):
                assert dukpy_install.main() == 2

    def test_install_unexisting_package(self):
        with self._patch_npm({}, {}):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("missing-package", "1", self.tmpdir)
        assert "Unable to fetch package metadata" in str(err.exception)

    def test_install_unexisting_version(self):
        with self._patch_npm(self._offline_registry(), self._offline_tarballs()):
            with self.assertRaises(dukpy_install.JSPackageInstallError):
                dukpy.install_jspackage("offline-package", "9999", self.tmpdir)

    def test_install_missing_or_empty_versions_metadata(self):
        for registry in ({}, {"versions": {}}):
            with self.subTest(registry=registry):
                with self._patch_npm({"offline-package": registry}, {}):
                    with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                        dukpy.install_jspackage(
                            "offline-package", "1.0.0", self.tmpdir
                        )
                assert err.exception.error_code == 2
                assert "does not provide version metadata" in str(err.exception)

    def test_install_missing_download_url(self):
        registry = {"versions": {"99.9.9": {}}}
        with self._patch_npm({"offline-package": registry}, {}):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("offline-package", "99.9.9", self.tmpdir)
        assert "Unable to detect a supported download url" in str(err.exception)

    def test_rejects_non_https_tarball_url(self):
        registry = {
            "versions": {
                "1.0.0": {"dist": {"tarball": "http://example.invalid/pkg.tgz"}}
            }
        }
        with self._patch_npm({"offline-package": registry}, {}):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("offline-package", "1.0.0", self.tmpdir)
        assert "must use an https URL" in str(err.exception)

    def test_rejects_tarball_path_traversal(self):
        url = "https://registry.npmjs.org/unsafe/-/unsafe-1.0.0.tgz"
        registry = {"versions": {"1.0.0": {"dist": {"tarball": url}}}}
        tarballs = {
            url: self._tarball({"../outside.js": "module.exports = {};"}, root=None)
        }

        with self._patch_npm({"unsafe": registry}, tarballs):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("unsafe", "1.0.0", self.tmpdir)
        assert "unsafe path" in str(err.exception)
        assert not os.path.exists(os.path.join(self.tmpdir, "..", "outside.js"))

    def test_rejects_posix_absolute_tarball_path_when_platform_isabs_misses_it(self):
        member = tarfile.TarInfo("/package/index.js")

        with mock.patch("dukpy.install.os.path.isabs", return_value=False):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy_install._safe_tar_member_path(member, self.tmpdir, "unsafe")
        assert "unsafe path" in str(err.exception)

    def test_rejects_tarball_with_multiple_roots(self):
        url = "https://registry.npmjs.org/unsafe/-/unsafe-1.0.0.tgz"
        registry = {"versions": {"1.0.0": {"dist": {"tarball": url}}}}
        tarballs = {
            url: self._tarball(
                {
                    "first/index.js": "module.exports = {};",
                    "second/index.js": "module.exports = {};",
                },
                root=None,
            )
        }

        with self._patch_npm({"unsafe": registry}, tarballs):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("unsafe", "1.0.0", self.tmpdir)
        assert "exactly one top-level directory" in str(err.exception)

    def test_rejects_destination_path_traversal(self):
        url = "https://registry.npmjs.org/unsafe/-/unsafe-1.0.0.tgz"
        registry = {"versions": {"1.0.0": {"dist": {"tarball": url}}}}
        tarballs = {
            url: self._tarball(
                {
                    "package.json": json.dumps({"main": "index.js"}),
                    "index.js": "module.exports = {};",
                }
            )
        }

        with self._patch_npm({"../unsafe": registry}, tarballs):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("../unsafe", "1.0.0", self.tmpdir)
        assert "outside destination" in str(err.exception)

    def test_rejects_scoped_package_parent_symlink_escape(self):
        modulesdir = os.path.join(self.tmpdir, "modules")
        outside = os.path.join(self.tmpdir, "outside")
        os.mkdir(modulesdir)
        os.mkdir(outside)
        try:
            os.symlink(outside, os.path.join(modulesdir, "@fixture"))
        except (AttributeError, NotImplementedError, OSError) as exc:
            self.skipTest("symlink not supported: {0}".format(exc))

        with self._patch_npm(self._scoped_registry(), self._scoped_tarballs()):
            with self.assertRaises(dukpy_install.JSPackageInstallError) as err:
                dukpy.install_jspackage("@fixture/scoped", "1.0.0", modulesdir)
        assert "symlink" in str(err.exception)
        assert not os.path.exists(os.path.join(outside, "scoped"))

    def _offline_registry(self):
        return {
            "offline-package": {
                "versions": {
                    "1.0.0": {
                        "dependencies": {"offline-dep": "^1.0.0"},
                        "dist": {
                            "tarball": (
                                "https://registry.npmjs.org/offline-package/-/"
                                "offline-package-1.0.0.tgz"
                            )
                        },
                    }
                }
            },
            "offline-dep": {
                "versions": {
                    "1.0.0": {
                        "dist": {
                            "tarball": (
                                "https://registry.npmjs.org/offline-dep/-/"
                                "offline-dep-1.0.0.tgz"
                            )
                        }
                    }
                }
            },
        }

    def _offline_tarballs(self):
        return {
            (
                "https://registry.npmjs.org/offline-package/-/"
                "offline-package-1.0.0.tgz"
            ): self._tarball(
                {
                    "package.json": json.dumps({"main": "index.js"}),
                    "index.js": (
                        "var dep = require('offline-dep'); "
                        "module.exports = {answer: dep.value + 2};"
                    ),
                }
            ),
            (
                "https://registry.npmjs.org/offline-dep/-/offline-dep-1.0.0.tgz"
            ): self._tarball(
                {
                    "package.json": json.dumps({"main": "index.js"}),
                    "index.js": "module.exports = {value: 40};",
                }
            ),
        }

    def _scoped_registry(self):
        return {
            "@fixture/scoped": {
                "versions": {
                    "1.0.0": {
                        "dist": {
                            "tarball": (
                                "https://registry.npmjs.org/@fixture/scoped/-/"
                                "scoped-1.0.0.tgz"
                            )
                        }
                    }
                }
            }
        }

    def _scoped_tarballs(self):
        return {
            (
                "https://registry.npmjs.org/@fixture/scoped/-/scoped-1.0.0.tgz"
            ): self._tarball(
                {
                    "package.json": json.dumps({"main": "index.js"}),
                    "index.js": "module.exports = {scoped: true};",
                }
            )
        }

    def _patch_npm(self, registries, tarballs):
        urls = {}
        for name, info in registries.items():
            urls[
                "https://registry.npmjs.org/{0}".format(
                    dukpy_install.quote_plus(name, safe="@")
                )
            ] = json.dumps(info).encode("utf-8")
        urls.update(tarballs)

        def fake_urlopen(url):
            if url not in urls:
                raise Exception("Not Found: {0}".format(url))
            return BytesIO(urls[url])

        return mock.patch("dukpy.install.urlopen", side_effect=fake_urlopen)

    def _tarball(self, files, root="package"):
        tarball = BytesIO()
        with tarfile.open(fileobj=tarball, mode="w:gz") as tb:
            for path, content in files.items():
                archive_path = path if root is None else "/".join((root, path))
                data = content.encode("utf-8")
                info = tarfile.TarInfo(archive_path)
                info.size = len(data)
                tb.addfile(info, BytesIO(data))
        return tarball.getvalue()


class TestVersionResolver(unittest.TestCase):
    VERSIONS = {
        "0.14.5": {},
        "0.13.0-rc2": {},
        "0.13.0-rc1": {},
        "0.14.0-beta3": {},
        "0.2.6": {},
        "0.2.5": {},
        "0.2.4": {},
        "0.2.3": {},
        "0.2.2": {},
        "0.2.1": {},
        "0.2.0": {},
        "0.1.2": {},
        "0.3.5": {},
        "0.10.0-rc1": {},
        "0.14.0": {},
        "0.10.0": {},
        "0.13.0-beta.2": {},
        "0.0.1": {},
        "0.14.3": {},
        "0.0.3": {},
        "0.0.2": {},
        "0.6.3": {},
        "0.6.2": {},
        "0.3.0": {},
        "0.6.0": {},
        "0.11.0": {},
        "0.11.1": {},
        "0.3.4": {},
        "0.7.1": {},
        "15.0.0": {},
        "15.0.1": {},
        "0.12.1": {},
        "0.12.0": {},
        "0.15.0-alpha.1": {},
        "0.5.1": {},
        "0.5.0": {},
        "0.13.3": {},
        "0.5.2": {},
        "0.13.1": {},
        "0.14.0-beta2": {},
        "0.14.4": {},
        "0.14.7": {},
        "0.14.0-beta1": {},
        "0.14.1": {},
        "15.0.0-rc.2": {},
        "15.0.0-rc.1": {},
        "0.14.2": {},
        "0.14.8": {},
        "0.9.0": {},
        "0.8.0": {},
        "0.14.0-rc1": {},
        "0.12.0-rc1": {},
        "0.6.1": {},
        "0.12.2": {},
        "0.11.2": {},
        "0.9.0-rc1": {},
        "0.13.2": {},
        "0.14.0-alpha2": {},
        "0.14.0-alpha1": {},
        "0.14.0-alpha3": {},
        "0.13.0-beta.1": {},
        "0.13.0-alpha.2": {},
        "0.13.0-alpha.1": {},
        "0.13.0": {},
        "0.7.0": {},
        "0.14.6": {},
        "0.11.0-rc1": {},
    }

    def test_tilde_versioning(self):
        ver = dukpy_install._resolve_version("~0.14.x", self.VERSIONS)
        assert ver == "0.14.8", ver

    def test_caret_versioning(self):
        ver = dukpy_install._resolve_version("^0.x", self.VERSIONS)
        assert ver == "0.14.8", ver

    def test_equality(self):
        ver = dukpy_install._resolve_version("0.2.4", self.VERSIONS)
        assert ver == "0.2.4", ver

    def test_last(self):
        ver = dukpy_install._resolve_version("", self.VERSIONS)
        assert ver == "15.0.1", ver
