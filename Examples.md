# Introduction #

There are actually two APIs exposed by this library.

The first API is a high level pythonic class-based interface that should seem comfortable to Python developers. If you are just getting started with python-libarchive, this is probably where you should start.

The second API is a low-level wrapper around libarchive. This wrapper provides access to the C API exposed by libarchive. A few additions or changes were made to allow easy consumption from Python, but otherwise, most libarchive example code will work (although with Python syntax). This API will be useful to those familiar with libarchive, or those that need functionality not available in the high level API.

# Using the high-level API #

The high level API provides a pythonic class-based interface for working with archives. On top of this is a very thin compatibility wrapper for the standard Python zipfile and tarfile modules. Since the standard Python zipfile and tarfile modules both present a different interface, so do the compatibility wrappers.

These compatibility wrappers are provided so that python-libarchive can be a drop-in replacement for the standard modules. A reason to use libarchive instead of the standard modules is that it provides native performance and better memory consumption. So if you already have code using one of these modules, you can sin many cases just replace the standard module with the libarchive alternative.

However, if you are developing a new project, it is recommended that you forgo the compatibility wrappers. Using the high-level API directly means you can support the many archive formats that libarchive does through the same standard interface.

The workhorse of the high-level API is the Archive class. This is a forward-only iterator that allows you to open an archive of any supported formant and iterate it's contents.

```
import libarchive

a = libarchive.Archive('my_archive.zip')
for entry in a:
    print entry.pathname
a.close()
```

python-libarchive is also a context manager, so the above could be written as:

```
import libarchive

with libarchive.Archive('my_archive.zip') as a:
    for entry in a:
        print entry.pathname
```

You can also extract files. However, you can only extract the current item. Once you have iterated past an entry, there is no going back.

```
import libarchive

with libarchive.Archive('my_archive.zip') as a:
    for entry in a:
        if entry.pathname == 'my_file.txt':
            print 'File Contents:', a.read()
```

Besides the read() method, there is also readpath() and readstream(). Readpath() will extract the file to a path or already opened file. Readstream() will return a file-like object that can be used to read chunks of the file. Larger files being read from the archive should probably use one of these functions instead of read() which will read then entire contents into memory.

Writing archives is also straightforward. You open an Archive() class then add files to it using one of the write**() methods.**

```
import libarchive

with libarchive.Archive('my_archive.zip', 'w') as a:
    for name in os.listdir('.'):
        a.write(libarchive.Entry(name), file(name, 'r').read())
```

Again, there is also a writepath() method which will write a file-like object or path directly to the archive. The above example could have been written as the following.

```
import libarchive

with libarchive.Archive('my_archive.zip', 'w') as a:
    for name in os.listdir('.'):
        a.writepath(libarchive.Entry(name), name)
```

In addition to the Archive class. There is also SeekableArchive. This class provides random access when reading an archive. It will remember where entries are located within the archive stream, and will close/reopen the stream and seek to the entry's location. So, you can extract an item directly. The first example can be written as follows.

```
import libarchive

with libarchive.SeekableArchive('my_archive.zip') as a:
    print 'File Contents:', a.read('my_file.txt')
```

There is overhead involved in using the SeekableArchive, so it is suggested that you use the Archive in cases that you don't need random access to an archives entries. In fact, the above example was probably better off using the Archive class.

# Using the low-level API #

Using the low-level API leaves all the work to you. You will need to be careful to create and free libarchive structures yourself. You will also need to be well-versed in the return codes and expected parameters of libarchive. In fact, if you are not, then you probably should stop reading now.

```
from libarchive import _libarchive

a = _libarchive.archive_read_new()
_libarchive.archive_read_support_filter_all(a)
_libarchive.archive_read_support_format_all(a)
_libarchive.archive_read_open_fd(a, f.fileno(), 10240)
while True:
    e = _libarchive.archive_entry_new()
    try:
        r = _libarchive.archive_read_next_header2(a, e)
        if r != _libarchive.ARCHIVE_OK:
            break
        n = _libarchive.archive_entry_pathname(e)
        if n != 'my_file.txt':
            continue
        l = _libarchive.archive_entry_size(e)
        s = _libarchive.archive_read_data_into_str(a, l)
        print 'File Contents:', s
    finally:
        _libarchive.archive_entry_free(e)
_libarchive.archive_read_close(a)
_libarchive.archive_read_free(a)
```

As you can see this is a lot more work for little benefit. But as stated before, you may end up interacting with the low-level API if some of the functionality you require is not covered in the high-level API.

And as always, patches are appreciated!