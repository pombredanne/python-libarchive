# Copyright (c) 2011, SmartFile <btimby@smartfile.com>
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the organization nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import os, sys, math, warnings, stat, time
from libarchive import _libarchive
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Suggested block size for libarchive. Libarchive may adjust it.
BLOCK_SIZE = 10240

MTIME_FORMAT = ''

# Default encoding scheme.
ENCODING = 'utf-8'

# Functions to initialize read/write for various libarchive supported formats and filters.
FORMATS = {
    None:       (_libarchive.archive_read_support_format_all, None),
    'tar':      (_libarchive.archive_read_support_format_tar, _libarchive.archive_write_set_format_ustar),
    'pax':      (_libarchive.archive_read_support_format_tar, _libarchive.archive_write_set_format_pax),
    'gnu':      (_libarchive.archive_read_support_format_gnutar, _libarchive.archive_write_set_format_gnutar),
    'zip':      (_libarchive.archive_read_support_format_zip, _libarchive.archive_write_set_format_zip),
    'rar':      (_libarchive.archive_read_support_format_rar, None),
    '7zip':     (_libarchive.archive_read_support_format_7zip, None),
    'ar':       (_libarchive.archive_read_support_format_ar, None),
    'cab':      (_libarchive.archive_read_support_format_cab, None),
    'cpio':     (_libarchive.archive_read_support_format_cpio, _libarchive.archive_write_set_format_cpio_newc),
    'iso':      (_libarchive.archive_read_support_format_iso9660, _libarchive.archive_write_set_format_iso9660),
    'lha':      (_libarchive.archive_read_support_format_lha, None),
    'xar':      (_libarchive.archive_read_support_format_xar, _libarchive.archive_write_set_format_xar),
}

FILTERS = {
    None:       (_libarchive.archive_read_support_filter_all, _libarchive.archive_write_add_filter_none),
    'gz':       (_libarchive.archive_read_support_filter_gzip, _libarchive.archive_write_add_filter_gzip),
    'bz2':      (_libarchive.archive_read_support_filter_bzip2, _libarchive.archive_write_add_filter_bzip2),
}

# Map file extensions to formats and filters. For supporting quick detection.
FORMAT_EXTENSIONS = {
    'tar':      ('.tar', ),
    'zip':      ('.zip', ),
    'rar':      ('.rar', ),
    '7zip':     ('.7z', ),
    'ar':       ('.ar', ),
    'cab':      ('.cab', ),
    'cpio':     ('.rpm', '.cpio'),
    'iso':      ('.iso', ),
    'lha':      ('.lha', ),
    'xar':      ('.xar', ),
}

FILTER_EXTENSIONS = {
    'gz':       ('.gz', ),
    'bz2':      ('.bz2', ),
}

class EOF(Exception):
    '''Raised by ArchiveInfo.from_archive() when unable to read the next
    archive header.'''
    pass


def get_error(archive):
    '''Retrieves the last error description for the given archive instance.'''
    return _libarchive.archive_error_string(archive)

def call_and_check(func, archive, *args):
    '''Executes a libarchive function and raises an exception when appropriate.'''
    ret = func(*args)
    if ret == _libarchive.ARCHIVE_OK:
        return
    elif ret == _libarchive.ARCHIVE_WARN:
        warnings.warn('Warning executing function: %s.' % get_error(archive), RuntimeWarning)
    elif ret == _libarchive.ARCHIVE_EOF:
        raise EOF()
    else:
        raise Exception('Fatal error executing function, message is: %s.' % get_error(archive))


def get_func(name, items, index):
    item = items.get(name, None)
    if item is None:
        return None
    return item[index]


def guess_format(filename):
    name, ext = os.path.splitext(filename)[1]
    for format, extensions in FORMAT_EXTENSIONS.items():
        if ext in extensions:
            return format


def is_archive_name(filename, formats=None):
    '''Quick check to see if the given file has an extension indiciating that it is
    an archive. The format parameter can be used to limit what archive format is acceptable.
    If omitted, all supported archive formats will be checked.

    This function will return the name of the most likely archive format, None if the file is
    unlikely to be an archive.'''
    filename, fileext = os.path.splitext(filename)
    exts = []
    map(exts.extend, FILTER_EXTENSIONS.values())
    if fileext in exts:
        filename, fileext = os.path.splitext(filename)
    if formats:
        for format in formats:
            exts = FORMAT_EXTENSIONS.get(format, [])
            if fileext not in exts:
                return format
    else:
        for format, exts in FORMAT_EXTENSIONS.items():
            if fileext in exts:
                return format


def is_archive(f, formats=(None, ), filters=(None, )):
    '''Check to see if the given file is actually an archive. The format parameter
    can be used to specify which archive format is acceptable. If ommitted, all supported
    archive formats will be checked. It opens the file using libarchive. If no error is
    received, the file was successfully detected by the libarchive bidding process.

    This procedure is quite costly, so you should avoid calling it unless you are reasonably
    sure that the given file is an archive. In other words, you may wish to filter large
    numbers of file names using is_archive_name() before double-checking the positives with
    this function.

    This function will return the name of the most likely archive format, None if the file is
    unlikely to be an archive.'''
    if isinstance(f, basestring):
        f = file(f, 'r')
    a = _libarchive.archive_read_new()
    for format in formats:
        format = get_func(format, FORMATS, 0)
        if format is None:
            return False
        format(a)
    for filter in filters:
        filter = get_func(filter, FILTERS, 0)
        if filter is None:
            return False
        filter(a)
    try:
        try:
            call_and_check(_libarchive.archive_read_open_fd, a, a, f.fileno(), BLOCK_SIZE)
            return True
        except:
            return False
    finally:
        _libarchive.archive_read_close(a)
        _libarchive.archive_read_free(a)


class EntryReadStream(object):
    '''A file-like object for reading an entry from the archive.'''
    def __init__(self, archive, size):
        self.archive = archive
        self.size = size
        self.bytes = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        return

    def __iter__(self):
        while True:
            data = self.read(BLOCK_SIZE)
            if not data:
                break
            yield data

    def read(self, bytes=None):
        if self.bytes == self.size:
            # EOF already reached.
            return
        if bytes is None:
            bytes = self.size - self.bytes
        elif self.bytes + bytes > self.size:
            # Limit read to remaining bytes
            bytes = self.size - self.bytes
        # Read requested bytes
        data = _libarchive.archive_read_data_into_str(self.archive._a, bytes)
        self.bytes += len(data)
        return data

    def close(self):
        pass # No-op

class EntryWriteStream(object):
    '''A file-like object for writing an entry to an archive.

    If the size is known ahead of time and provided, then the file contents
    are not buffered but flushed directly to the archive. If size is omitted,
    then the file contents are buffered and flushed in the close() method.'''
    def __init__(self, archive, pathname, size=None):
        self.archive = archive
        self.entry = Entry(pathname=pathname, mtime=time.time(), mode=stat.S_IFREG)
        if size is None:
            self.buffer = StringIO()
        else:
            self.buffer = None
            self.entry.size = size
            self.entry.to_archive(self.archive)
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def write(self, data):
        if self.closed:
            raise Exception('Cannot write to closed stream.')
        if self.buffer:
            self.buffer.write(data)
        else:
            _libarchive.archive_write_data_from_str(self.archive._a, data)

    def close(self):
        if self.closed:
            return
        if self.buffer:
            self.entry.size = self.buffer.tell()
            self.entry.to_archive(self.archive)
            _libarchive.archive_write_data_from_str(self.archive._a, self.buffer.getvalue())
        _libarchive.archive_write_finish_entry(self.archive._a)
        self.closed = True


class Entry(object):
    '''An entry within an archive. Represents the header data and it's location within the archive.'''
    def __init__(self, pathname=None, size=None, mtime=None, mode=None, hpos=None, encoding=ENCODING):
        self.pathname = pathname
        self.size = size
        self.mtime = mtime
        self.mode = mode
        self.hpos = hpos
        self.encoding = encoding

    @property
    def header_position(self):
        return self.hpos

    @classmethod
    def from_archive(cls, archive, encoding=ENCODING):
        '''Instantiates an Entry class and sets all the properties from an archive header.'''
        e = _libarchive.archive_entry_new()
        try:
            call_and_check(_libarchive.archive_read_next_header2, archive._a, archive._a, e)
            mode = _libarchive.archive_entry_filetype(e)
            mode |= _libarchive.archive_entry_perm(e)
            entry = cls(
                pathname = _libarchive.archive_entry_pathname(e).decode(encoding),
                size = _libarchive.archive_entry_size(e),
                mtime = _libarchive.archive_entry_mtime(e),
                mode = mode,
                hpos = archive.header_position,
            )
        finally:
            _libarchive.archive_entry_free(e)
        return entry

    @classmethod
    def from_file(cls, f, entry=None, encoding=ENCODING):
        '''Instantiates an Entry class and sets all the properties from a file on the file system.
        f can be a file-like object or a path.'''
        if entry is None:
            entry = cls(encoding=encoding)
        if entry.pathname is None:
            if isinstance(f, basestring):
                entry.pathname = f
                st = os.stat(f)
            else:
                entry.pathname = getattr(f, 'name', None)
                st = os.fstat(f.fileno())
        entry.size = st.st_size
        entry.mtime = st.st_mtime
        entry.mode = st.st_mode
        return entry

    def to_archive(self, archive):
        '''Creates an archive header and writes it to the given archive.'''
        e = _libarchive.archive_entry_new()
        try:
            _libarchive.archive_entry_set_pathname(e, self.pathname.encode(self.encoding))
            _libarchive.archive_entry_set_filetype(e, stat.S_IFMT(self.mode))
            _libarchive.archive_entry_set_perm(e, stat.S_IMODE(self.mode))
            _libarchive.archive_entry_set_size(e, self.size)
            _libarchive.archive_entry_set_mtime(e, self.mtime, 0)
            call_and_check(_libarchive.archive_write_header, archive._a, archive._a, e)
            #self.hpos = archive.header_position
        finally:
            _libarchive.archive_entry_free(e)

    def isdir(self):
        return stat.S_ISDIR(self.mode)

    def isfile(self):
        return stat.S_ISREG(self.mode)

    def issym(self):
        return stat.S_ISLNK(self.mode)

    def isfifo(self):
        return stat.S_ISFIFO(self.mode)

    def ischr(self):
        return stat.S_ISCHR(self.mode)

    def isblk(self):
        return stat.S_ISBLK(self.mode)


class Archive(object):
    '''A low-level archive reader which provides forward-only iteration. Consider
    this a light-weight pythonic libarchive wrapper.'''
    def __init__(self, f, mode='r', format=None, filter=None, entry_class=Entry, encoding=ENCODING, blocksize=BLOCK_SIZE):
        assert mode in ('r', 'w', 'wb', 'a'), 'Mode should be "r", "w", "wb", or "a".'
        self.encoding = encoding
        self.blocksize = blocksize
        if isinstance(f, basestring):
            self.filename = f
            f = file(f, mode)
            # Only close it if we opened it...
            self._close = True
        elif hasattr(f, 'fileno'):
            self.filename = getattr(f, 'name', None)
            # Leave the fd alone, caller should manage it...
            self._close = False
        else:
            raise Exception('Provided file is not path or open file.')
        self.f = f
        self.mode = mode
        self.format = format
        self.filter = filter
        self.entry_class = entry_class
        if self.mode == 'r':
            self.format_func = get_func(self.format, FORMATS, 0)
            if self.format_func is None:
                raise Exception('Unsupported format %s' % format)
            self.filter_func = get_func(self.filter, FILTERS, 0)
            if self.filter_func is None:
                raise Exception('Unsupported filter %s' % filter)
        else:
            # TODO: how to support appending?
            if self.format is None and self.filename:
                # Try to guess format by file extension:
                self.format = guess_format(self.filename)
            if self.format is None:
                raise Exception('You must specify a format for writing.')
            self.format_func = get_func(self.format, FORMATS, 1)
            if self.format_func is None:
                raise Exception('Unsupported format %s' % format)
            self.filter_func = get_func(self.filter, FILTERS, 1)
            if self.filter_func is None:
                raise Exception('Unsupported filter %s' % filter)
        self.init()

    def __iter__(self):
        while True:
            try:
                yield self.entry_class.from_archive(self, encoding=self.encoding)
            except EOF:
                break

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.denit()

    def __del__(self):
        self.close()

    def init(self):
        if self.mode == 'r':
            self._a = _libarchive.archive_read_new()
        else:
            self._a = _libarchive.archive_write_new()
        self.format_func(self._a)
        self.filter_func(self._a)
        if self.mode == 'r':
            call_and_check(_libarchive.archive_read_open_fd, self._a, self._a, self.f.fileno(), self.blocksize)
        else:
            call_and_check(_libarchive.archive_write_open_fd, self._a, self._a, self.f.fileno())

    def denit(self):
        '''Closes and deallocates the archive reader/writer.'''
        if getattr(self, '_a', None) is None:
            return
        if self.mode == 'r':
            _libarchive.archive_read_close(self._a)
            _libarchive.archive_read_free(self._a)
        elif self.mode == 'w':
            _libarchive.archive_write_close(self._a)
            _libarchive.archive_write_free(self._a)
        self._a = None

    def close(self):
        self.denit()
        if self._close and hasattr(self, 'f'):
            # Only close once:
            self._close = False
            self.f.close()
        self.f.flush()

    @property
    def header_position(self):
        '''The position within the file.'''
        return _libarchive.archive_read_header_position(self._a)

    def iterpaths(self):
        for entry in self:
            yield entry.pathname

    def read(self, size):
        '''Read current archive entry contents into string.'''
        return _libarchive.archive_read_data_into_str(self._a, size)

    def readpath(self, f):
        '''Write current archive entry contents to file. f can be a file-like object or
        a path.'''
        if isinstance(f, basestring):
            basedir = os.path.basename(f)
            if not os.path.exists(basedir) :
                os.makedirs(basedir)
            f = file(f, 'w')
        fd = fd.fileno()
        ret = _libarchive.archive_read_data_into_fd(self._a, fd)

    def readstream(self, size):
        '''Returns a file-like object for reading current archive entry contents.'''
        return EntryReadStream(self, size)

    def write(self, member, data=None):
        '''Writes a string buffer to the archive as the given entry.'''
        if isinstance(member, basestring):
            member = self.entry_class(pathname=member, encoding=self.encoding)
        if data:
            member.size = len(data)
        member.to_archive(self)
        if data:
            _libarchive.archive_write_data_from_str(self._a, data)
        _libarchive.archive_write_finish_entry(self._a)

    def writepath(self, f, pathname=None):
        '''Writes a file to the archive. f can be a file-like object or a path. Uses
        write() to do the actual writing.'''
        member = self.entry_class.from_file(f, encoding=self.encoding)
        if isinstance(f, basestring):
            if os.path.isfile(f):
                f = file(f, 'r')
        if pathname:
            member.pathname = pathname
        if hasattr(f, 'read'):
            # TODO: optimize this to write directly from f to archive.
            self.write(member, data=f.read())
        else:
            self.write(member)

    def writestream(self, pathname, size=None):
        '''Returns a file-like object for writing a new entry.'''
        return EntryWriteStream(self, pathname, size)

    def printlist(self, s=sys.stdout):
        for entry in self:
            s.write(entry.size)
            s.write('\t')
            s.write(entry.mtime.strftime(MTIME_FORMAT))
            s.write('\t')
            s.write(entry.pathname)
        s.flush()


class SeekableArchive(Archive): 
    '''A class that provides random-access to archive entries. It does this by using one
    or many Archive instances to seek to the correct location. The best performance will
    occur when reading archive entries in the order in which they appear in the archive.
    Reading out of order will cause the archive to be closed and opened each time a
    reverse seek is needed.'''
    def __init__(self, f, **kwargs):
        # Convert file to open file. We need this to reopen the archive.
        mode = kwargs.setdefault('mode', 'r')
        if isinstance(f, basestring):
            f = file(f, mode)
        super(SeekableArchive, self).__init__(f, **kwargs)
        self.entries = []
        self.eof = False

    def __iter__(self):
        for entry in self.entries:
            yield entry
        if not self.eof:
            try:
                for entry in super(SeekableArchive, self).__iter__():
                    self.entries.append(entry)
                    yield entry
            except StopIteration:
                self.eof = True

    def reopen(self):
        '''Seeks the underlying fd to 0 position, then opens the archive. If the archive
        is already open, this will effectively re-open it (rewind to the beginning).'''
        self.denit();
        self.f.seek(0)
        self.init()

    def getentry(self, pathname):
        '''Take a name or entry object and returns an entry object.'''
        for entry in self:
            if entry.pathname == pathname:
                return entry
        raise KeyError(pathname)

    def seek(self, entry):
        '''Seeks the archive to the requested entry. Will reopen if necessary.'''
        move = entry.header_position - self.header_position
        if move != 0:
            if move < 0:
                # can't move back, re-open archive:
                self.reopen()
            # move to proper position in stream
            for curr in super(SeekableArchive, self).__iter__():
                if curr.header_position == entry.header_position:
                    break

    def read(self, member):
        '''Return the requested archive entry contents as a string.'''
        entry = self.getentry(member)
        self.seek(entry)
        return super(SeekableArchive, self).read(entry.size)

    def readpath(self, member, f):
        entry = self.getentry(member)
        self.seek(entry)
        return super(SeekableArchive, self).readpath(f)

    def readstream(self, member):
        '''Returns a file-like object for reading requested archive entry contents.'''
        entry = self.getentry(member)
        self.seek(entry)
        return EntryReadStream(self, entry.size)

