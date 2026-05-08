# -*- coding: utf-8 -*-
from __future__ import print_function
import argparse
import json
import os
import posixpath
import sys
import tarfile
import tempfile
import shutil
from contextlib import closing
from io import BytesIO
from .evaljs import evaljs

try:
    from urllib.request import urlopen
    from urllib.parse import quote_plus, urlparse
except ImportError:  # pragma: no cover
    from urllib2 import urlopen
    from urllib import quote_plus
    from urlparse import urlparse


def main():
    parser = argparse.ArgumentParser(
        description="Install a Javascript Package from npmjs.org"
    )
    parser.add_argument("package_name", help="name of the package to install")
    parser.add_argument(
        "version", nargs="?", help="Version of the package (omit for latest)"
    )
    parser.add_argument(
        "--destination",
        "-d",
        default="./js_modules",
        help="directory where to install javascript packages",
    )
    args = parser.parse_args(sys.argv[1:])

    try:
        return install_jspackage(args.package_name, args.version, args.destination)
    except JSPackageInstallError as e:
        print(e)
        return e.error_code


def install_jspackage(package_name, version, modulesdir):
    """Installs a JavaScript package downloaded from npmjs.org.

    For example to install React::

        install_jspackage('react', '0.14.8', './node_modules')

    To install last version provide `None` as the version.
    """
    if not version:
        version = ""

    requirements = _resolve_dependencies(package_name, version)
    print(
        "Packages going to be installed: {0}".format(
            ", ".join("{0}->{1}".format(*i) for i in requirements)
        )
    )

    downloads = {}
    for dependency_name, _, version_info in requirements:
        try:
            download_url = version_info["dist"]["tarball"]
        except KeyError:
            raise JSPackageInstallError(
                "Unable to detect a supported download url for package {0}".format(
                    dependency_name
                ),
                error_code=3,
            )
        _require_https_url(download_url, "Package tarball")
        downloads[dependency_name] = download_url

    modulesdir = os.path.abspath(modulesdir)
    for dependency_name, download_url in downloads.items():
        dest = _package_destination(modulesdir, dependency_name)
        tarball = _download_tarball(download_url)
        tmpdir = tempfile.mkdtemp()
        try:
            package_root = _extract_package_root(tarball, tmpdir, dependency_name)
            _prepare_package_destination(modulesdir, dest, dependency_name)
            shutil.rmtree(dest, ignore_errors=True)
            shutil.move(package_root, dest)
        except JSPackageInstallError:
            raise
        except (IOError, OSError) as e:
            raise JSPackageInstallError(
                "Unable to install package {0}: {1}".format(dependency_name, e),
                error_code=3,
            )
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    print("Installing {0} in {1} Done!".format(package_name, modulesdir))


class JSPackageInstallError(Exception):
    def __init__(self, msg, error_code):
        super(JSPackageInstallError, self).__init__(msg)
        self.error_code = error_code


def _download_tarball(download_url):
    tarball = BytesIO()
    print("Fetching {0}".format(download_url), end="")
    try:
        with closing(urlopen(download_url)) as data:
            chunk = data.read(1024)
            while chunk:
                print(".", end="")
                tarball.write(chunk)
                chunk = data.read(1024)
    except Exception as e:
        raise JSPackageInstallError(
            "Unable to download package tarball from {0}: {1}".format(
                download_url, e
            ),
            error_code=3,
        )
    print("")
    tarball.seek(0)
    return tarball


def _extract_package_root(tarball, tmpdir, package_name):
    try:
        with closing(tarfile.open(fileobj=tarball, mode="r:*")) as tb:
            members = tb.getmembers()
            roots = set()
            tmpdir = os.path.abspath(tmpdir)
            for member in members:
                path = _safe_tar_member_path(member, tmpdir, package_name)
                root = posixpath.normpath(member.name).split("/")[0]
                if root:
                    roots.add(root)
                member.name = path
            if len(roots) != 1:
                raise JSPackageInstallError(
                    "Package archive for {0} must contain exactly one top-level "
                    "directory".format(package_name),
                    error_code=3,
                )
            tb.extractall(tmpdir, members)
            package_root = os.path.join(tmpdir, roots.pop())
            if not os.path.isdir(package_root):
                raise JSPackageInstallError(
                    "Package archive for {0} must contain one top-level directory".format(
                        package_name
                    ),
                    error_code=3,
                )
            return package_root
    except tarfile.TarError as e:
        raise JSPackageInstallError(
            "Unable to read package archive for {0}: {1}".format(package_name, e),
            error_code=3,
        )


def _safe_tar_member_path(member, tmpdir, package_name):
    if not (member.isfile() or member.isdir()):
        raise JSPackageInstallError(
            "Package archive for {0} contains unsupported entry {1}".format(
                package_name, member.name
            ),
            error_code=3,
        )
    normalized = posixpath.normpath(member.name)
    parts = normalized.split("/")
    if (
        "\\" in member.name
        or os.path.isabs(member.name)
        or posixpath.isabs(normalized)
        or parts[0] == ""
        or normalized in ("", ".")
        or ".." in parts
    ):
        raise JSPackageInstallError(
            "Package archive for {0} contains unsafe path {1}".format(
                package_name, member.name
            ),
            error_code=3,
        )

    destination = os.path.abspath(os.path.join(tmpdir, *parts))
    if os.path.commonpath((tmpdir, destination)) != tmpdir:
        raise JSPackageInstallError(
            "Package archive for {0} contains unsafe path {1}".format(
                package_name, member.name
            ),
            error_code=3,
        )
    return normalized


def _package_destination(modulesdir, package_name):
    dest = os.path.abspath(os.path.join(modulesdir, package_name))
    _validate_package_destination(modulesdir, dest, package_name)
    return dest


def _prepare_package_destination(modulesdir, dest, package_name):
    dest_parent = os.path.dirname(dest)
    _validate_package_destination(modulesdir, dest, package_name)
    if not os.path.isdir(dest_parent):
        os.makedirs(dest_parent)
    _validate_package_destination(modulesdir, dest, package_name)


def _validate_package_destination(modulesdir, dest, package_name):
    if os.path.commonpath((modulesdir, dest)) != modulesdir:
        raise JSPackageInstallError(
            "Refusing to install package outside destination: {0}".format(
                package_name
            ),
            error_code=3,
        )
    if os.path.islink(dest):
        raise JSPackageInstallError(
            "Refusing to install package over symlinked destination: {0}".format(
                package_name
            ),
            error_code=3,
        )

    dest_parent = os.path.dirname(dest)
    relative_parent = os.path.relpath(dest_parent, modulesdir)
    if relative_parent != os.curdir:
        current = modulesdir
        for path_part in relative_parent.split(os.sep):
            current = os.path.join(current, path_part)
            if os.path.islink(current):
                raise JSPackageInstallError(
                    "Refusing to install package through symlinked parent: {0}".format(
                        package_name
                    ),
                    error_code=3,
                )

    real_modulesdir = os.path.realpath(modulesdir)
    real_dest_parent = os.path.realpath(dest_parent)
    if os.path.commonpath((real_modulesdir, real_dest_parent)) != real_modulesdir:
        raise JSPackageInstallError(
            "Refusing to install package outside destination: {0}".format(
                package_name
            ),
            error_code=3,
        )


def _require_https_url(url, description):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise JSPackageInstallError(
            "{0} must use an https URL: {1}".format(description, url), error_code=3
        )


def _resolve_version(version, versions):
    return evaljs(
        """
        var semver = require('semver');
        semver.maxSatisfying(dukpy.versions, dukpy.version)
    """,
        version=version,
        versions=list(versions.keys()),
    )


def _fetch_package_info(package_name):
    url = "https://registry.npmjs.org/{0}".format(package_name)
    _require_https_url(url, "npm registry")
    try:
        with closing(urlopen(url)) as data:
            return json.loads(data.read().decode("utf-8"))
    except Exception as e:
        raise JSPackageInstallError(
            "Unable to fetch package metadata for {0}: {1}".format(package_name, e),
            error_code=3,
        )


def _resolve_dependencies(package_name, version):
    package_info = _fetch_package_info(quote_plus(package_name, safe="@"))
    package_versions = package_info.get("versions")
    if not isinstance(package_versions, dict) or not package_versions:
        raise JSPackageInstallError(
            "Package {0} does not provide version metadata".format(package_name),
            error_code=2,
        )
    matching_version = _resolve_version(version, package_versions)
    version_info = package_versions.get(matching_version)
    if version_info is None:
        raise JSPackageInstallError(
            "Version {0} not found, available versions are {1}".format(
                version, ", ".join(sorted(package_versions.keys()))
            ),
            error_code=2,
        )

    requirements = [(package_name, matching_version, version_info)]
    dependencies = version_info.get("dependencies", {})
    if dependencies:
        for dependency, dependency_version in dependencies.items():
            requirements.extend(_resolve_dependencies(dependency, dependency_version))
    return requirements
