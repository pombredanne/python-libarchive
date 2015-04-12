A [SmartFile](http://www.smartfile.com/) Open Source project. [Read more](http://www.smartfile.com/open-source.html) about how SmartFile uses and contributes to Open Source software.

![http://www.smartfile.com/images/logo.jpg](http://www.smartfile.com/images/logo.jpg)

Fully functional Python wrapper for [libarchive](http://code.google.com/p/libarchive). Created using SWIG. The low-level API provides access to all of the functionality of [libarchive](http://code.google.com/p/libarchive).

The package also includes a high level python library which mimics the [zipfile](http://docs.python.org/library/zipfile.html) and [tarfile](http://docs.python.org/library/tarfile.html) modules.

Libarchive supports the following:

  * Reads a variety of formats, including tar, pax, cpio, zip, xar, lha, ar, cab, mtree, rar, and ISO images.
  * Writes tar, pax, cpio, zip, xar, ar, ISO, mtree, and shar archives.
  * Automatically handles archives compressed with gzip, bzip2, lzip, xz, lzma, or compress.

Get started by reading the [Examples](Examples.md). Then move on to [Building](Building.md).

If you are interested in interfacing with archives using a file system type interface, take a look at [pyFilesystem](http://code.google.com/p/pyfilesystem/). This module provides a standard interface to many file systems implemented as part of the library. Using pyFilesystem, you can interact with WebDAV, archives, S3 or even regular file systems using a common API. There is a file system for pyFilesystem named [ArchiveFS](http://code.google.com/p/pyfilesystem/source/browse/trunk/fs/contrib/archivefs.py) which utilizes python-libarchive.