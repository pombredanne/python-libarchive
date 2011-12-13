#!/usr/bin/env python

import os, sys
try:
    from setuptools import setup, Extension
    from setuptools.command import build_ext
except ImportError:
    from distutils.core import setup, Extension
    from distutils.command import build_ext

_libarchive = Extension(name='_libarchive',
                        sources=['libarchive/_libarchive.i'],
                        extra_compile_args=['-Ilibarchive'],
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

      ext_modules = [_libarchive],
      )