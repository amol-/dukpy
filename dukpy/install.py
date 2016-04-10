# -*- coding: utf-8 -*-
from __future__ import print_function
import json
import os
import sys
import tarfile
import tempfile
import shutil
from contextlib import closing
from io import BytesIO

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen


def main():
    args = sys.argv[1:]
    try:
        package_name = args[0]
        version = args[1]
    except:
        print('Usage: dukpy-install package_name version')
        print('')
        print('Downloads a specific package version from npmjs.org. Note this is'
              'a very basic script that does not support dependencies.')
        return 1

    install_jspackage(package_name, version, './node_modules')


def install_jspackage(package_name, version, modulesdir):
    """Installs a JavaScript package downloaded from npmjs.org.

    For example to install React::

        install_jspackage('react', '0.14.8', './node_modules')
    """
    url = 'http://registry.npmjs.org/{0}'
    with closing(urlopen(url.format(package_name))) as data:
        package_info = json.loads(data.read().decode('utf-8'))
        package_versions = package_info['versions']
        version_info = package_versions.get(version)
        if version_info is None:
            print('Version {0} not found, available versions are {1}'.format(
                version, ', '.join(sorted(package_versions.keys()))
            ))
            return 2

        try:
            download_url = version_info['dist']['tarball']
        except KeyError:
            print('Unable to detect a supported download url for package')
            return 3

        tarball = BytesIO()
        print('Downloading {0}'.format(download_url))
        with closing(urlopen(download_url)) as data:
            chunk = data.read(1024)
            while chunk:
                print('.', end='')
                tarball.write(chunk)
                chunk = data.read(1024)
        print('')

        tarball.seek(0)
        print('Extracting... ')
        with tarfile.open(fileobj=tarball) as tb:
            dest = os.path.join(modulesdir, version_info['name'])
            tmpdir = tempfile.mkdtemp()
            try:
                tb.extractall(tmpdir)
                shutil.move(os.path.join(tmpdir, 'package'),
                            os.path.abspath(dest))
            finally:
                shutil.rmtree(tmpdir)

        print('Installed in {0}'.format(dest))

