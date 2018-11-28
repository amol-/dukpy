# -*- coding: utf-8 -*-
from __future__ import print_function
import argparse
import json
import os
import sys
import tarfile
import tempfile
import shutil
from contextlib import closing
from io import BytesIO
from .evaljs import evaljs

try:
    from urllib.request import urlopen
    from urllib.parse import quote_plus
except ImportError:  # pragma: no cover
    from urllib2 import urlopen
    from urllib import quote_plus


def main():
    parser = argparse.ArgumentParser(description='Install a Javascript Package from npmjs.org')
    parser.add_argument('package_name',
                        help='name of the package to install')
    parser.add_argument('version', nargs='?',
                        help='Version of the package (omit for latest)')
    parser.add_argument('--destination', '-d', default='./js_modules',
                        help="directory where to install javascript packages")
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
        version = ''

    requirements = _resolve_dependencies(package_name, version)
    print('Packages going to be installed: {0}'.format(', '.join(
        '{0}->{1}'.format(*i) for i in requirements
    )))

    downloads = {}
    for dependency_name, _, version_info in requirements:
        try:
            downloads[dependency_name] = version_info['dist']['tarball']
        except KeyError:
            raise JSPackageInstallError('Unable to detect a supported download url for package',
                                        error_code=3)

    for dependency_name, download_url in downloads.items():
        tarball = BytesIO()
        print('Fetching {0}'.format(download_url), end='')
        with closing(urlopen(download_url)) as data:
            chunk = data.read(1024)
            while chunk:
                print('.', end='')
                tarball.write(chunk)
                chunk = data.read(1024)
        print('')

        tarball.seek(0)
        with closing(tarfile.open(fileobj=tarball)) as tb:
            dest = os.path.join(modulesdir, dependency_name)
            tmpdir = tempfile.mkdtemp()
            try:
                tb.extractall(tmpdir)
                shutil.rmtree(os.path.abspath(dest), ignore_errors=True)
                shutil.move(os.path.join(tmpdir, 'package'),
                            os.path.abspath(dest))
            finally:
                shutil.rmtree(tmpdir)

    print('Installing {0} in {1} Done!'.format(package_name, modulesdir))


def _resolve_version(version, versions):
    return evaljs('''
        var semver = require('semver');
        semver.maxSatisfying(dukpy.versions, dukpy.version)
    ''', version=version, versions=list(versions.keys()))


def _fetch_package_info(package_name):
    url = 'http://registry.npmjs.org/{0}'
    with closing(urlopen(url.format(package_name))) as data:
        return json.loads(data.read().decode('utf-8'))


def _resolve_dependencies(package_name, version):
    package_info = _fetch_package_info(quote_plus(package_name, safe='@'))
    package_versions = package_info['versions']
    matching_version = _resolve_version(version, package_versions)
    version_info = package_versions.get(matching_version)
    if version_info is None:
        raise JSPackageInstallError('Version {0} not found, available versions are {1}'.format(
            version, ', '.join(sorted(package_versions.keys()))
        ), error_code=2)

    requirements = [(package_name, matching_version, version_info)]
    dependencies = version_info.get('dependencies', {})
    if dependencies:
        for dependency, dependency_version in dependencies.items():
            requirements.extend(
                _resolve_dependencies(dependency, dependency_version)
            )
    return requirements


class JSPackageInstallError(Exception):
    def __init__(self, msg, error_code):
        super(JSPackageInstallError, self).__init__(msg)
        self.error_code = error_code
