#!/usr/bin/env python

import os, sys
try:
    from setuptools import setup, Extension
    from setuptools.command import build_ext
    from setuptools.command.build import build
    from setuptools.command.install_lib import install_lib
except ImportError:
    from distutils.core import setup, Extension
    from distutils.command import build_ext
    from distutils.command.build import build
    from distutils.command.install_lib import install_lib

# <monkey-patching>
# http://sourceforge.net/mailarchive/message.php?msg_id=28474701
# hack distutils so that extensions are built before python modules;
# this is necessary for SWIG-generated .py files
build.sub_commands = [('build_ext', build.has_ext_modules),
                     ('build_py', build.has_pure_modules),
                     ('build_clib', build.has_c_libraries),
                     ('build_scripts', build.has_scripts)]

def _build(self):
    if not self.skip_build:
        if self.distribution.has_ext_modules():
            self.run_command('build_ext')
        if self.distribution.has_pure_modules():
            self.run_command('build_py')

install_lib.build = _build

# </monkey-patching>

__libarchive = Extension(name='libarchive.__libarchive',
                        sources=['libarchive/_libarchive.i'],
                        extra_compile_args=['-Ilibarchive'],
                        extra_link_args=['-l:libarchive.so.11.0.1'],
                        )


setup(name = 'python-libarchive',
      version = '0.1',
      description = 'A LibArchive wrapper for Python.',
      long_description = '''\
A complete wrapper for the LibArchive library generated using SWIG.
Also included in the package are compatibility layers for the Python
zipfile and tarfile modules.''',
      license = 'BSD-style license',
      platforms = ['any'],
      author = 'Ben Timby',
      author_email = 'btimby at gmail dot com',
      url = 'http://code.google.com/p/python-libarchive/',
      packages = ['libarchive'],
      classifiers = [
          'Development Status :: 4 - Beta',
          'Intended Audience :: Developers',
          'Operating System :: OS Independent',
          'Programming Language :: C',
          'Programming Language :: Python',
          'Topic :: Data :: Compression',
          'Topic :: Software Development :: Libraries :: Python Modules',
      ],
      ext_modules = [__libarchive],
      )
