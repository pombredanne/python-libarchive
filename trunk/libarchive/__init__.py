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

import os, math, warnings, stat, time
from libarchive import _libarchive
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

# Suggested block size for libarchive. Libarchive may adjust it.
BLOCK_SIZE = 10240

ENCODING = 'utf-8'

# Functions to initialize read/write for various libarchive supported formats and filters.
FORMATS = {
    None:       (_libarchive.archive_read_support_format_all, None),
    'tar':      (_libarchive.archive_read_support_format_tar, _libarchive.archive_write_set_format_gnutar),
    'zip':      (_libarchive.archive_read_support_format_zip, _libarchive.archive_write_set_format_zip),
    'rar':      (_libarchive.archive_read_support_format_rar, None),
}

FILTERS = {
    None:       (_libarchive.archive_read_support_filter_all, _libarchive.archive_write_add_filter_none),
}

def get_error(archive):
    '''Retrieves the last error description for the given archive instance.'''
    return _libarchive.archive_error_string(archive)

def exec_and_check(func, archive, *args):
    '''Executes a libarchive function and raises an exception when appropriate.'''
    ret = func(*args)
    if ret == _libarchive.ARCHIVE_OK:
        return
    elif ret == _libarchive.ARCHIVE_WARN:
        warnings.warn('Warning executing function: %s.' % get_error(archive), RuntimeWarning)
    elif ret == _libarchive.ARCHIVE_EOF:
        raise EOF()
    else:
        raise Exception('Error executing function: %s.' % get_error(archive))


class EOF(Exception):
    '''Raised by ArchiveInfo.from_archive() when unable to read the next
    archive header.'''
    pass


class EntryReadStream(object):
    '''A file-like object for reading an entry from the archive.'''
    def __init__(self, size, read_func):
        self.size = size
        self.read_func = read_func
        self.bytes = 0

    def read(self, bytes=BLOCK_SIZE):
        if self.bytes == self.size:
            # EOF already reached.
            return
        if self.bytes + bytes > self.size:
            # Limit read to remaining bytes
            bytes = self.size - self.bytes
        # Read requested bytes
        data = self.read_func(bytes)
        self.bytes += len(data)
        return data


class EntryWriteStream(object):
    '''A file-like object that buffers writes until it is closed. Upon closing this object
    will add itself as a new entry to the provided archive.'''
    def __init__(self, pathname, write_func):
        self.pathname = pathname
        self.write_func = write_func
        # TODO: figure out how to write block-by-block (no buffering).
        self.stream = StringIO()

    def write(self, data):
        self.stream.write(data)

    def close(self):
        entry = Entry(pathname=self.pathname)
        entry.size = self.stream.tell()
        entry.mtime = time.time()
        entry.mode = stat.S_IFREG
        self.write_func(entry, self.stream.getvalue())


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
            exec_and_check(_libarchive.archive_read_next_header2, archive._a, archive._a, e)
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
            exec_and_check(_libarchive.archive_write_header, archive._a, archive._a, e)
            #self.hpos = archive.header_position
        finally:
            _libarchive.archive_entry_free(e)


class Archive(object):
    '''A low-level archive reader which provides forward-only iteration. Consider
    this a light-weight pythonic libarchive wrapper.'''
    def __init__(self, f, mode='r', format=None, filter=None, entry_class=Entry, encoding=ENCODING):
        assert mode in ('r', 'w', 'wb', 'a'), 'Mode should be "r", "w", "wb", or "a".'
        self.encoding = encoding
        if isinstance(f, basestring):
            self.filename = f
            f = file(f, mode)
        elif hasattr(f, 'fileno'):
            self.filename = getattr(f, 'name', None)
        else:
            raise Exception('Provided file is not path or open file.')
        self.f = f
        self.mode = mode
        self.entry_class = entry_class
        formats = FORMATS.get(format, None)
        filters = FILTERS.get(filter, None)
        if self.mode == 'r':
            if formats is None:
                raise Exception('Unsupported format %s' % format)
            if filters is None:
                raise Exception('Unsupported filter %s' % filter)
            self.format = formats[0]
            self.filter = filters[0]
        else:
            # TODO: how to support appending?
            if formats is None:
                raise Exception('Unsupported format %s' % format)
            if filters is None:
                raise Exception('Unsupported filter %s' % filter)
            if formats[1] is None:
                raise Exception('Cannot write specified format.')
            self.format = formats[1]
            self.filter = filters[1]
        self.open()

    def open(self):
        if self.mode == 'r':
            self._a = _libarchive.archive_read_new()
        else:
            self._a = _libarchive.archive_write_new()
        self.format(self._a)
        self.filter(self._a)
        if self.mode == 'r':
            exec_and_check(_libarchive.archive_read_open_fd, self._a, self._a, self.f.fileno(), BLOCK_SIZE)
        else:
            exec_and_check(_libarchive.archive_write_open_fd, self._a, self._a, self.f.fileno())

    def __iter__(self):
        while True:
            try:
                yield self.entry_class.from_archive(self, encoding=self.encoding)
            except EOF:
                break

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        '''Closes and deallocates the archive reader/writer.'''
        if self._a is None:
            return
        if self.mode == 'r':
            _libarchive.archive_read_close(self._a)
            _libarchive.archive_read_free(self._a)
        elif self.mode == 'w':
            _libarchive.archive_write_close(self._a)
            _libarchive.archive_write_free(self._a)
        self._a = None

    @property
    def header_position(self):
        '''The position within the file.'''
        return _libarchive.archive_read_header_position(self._a)

    def read(self, size):
        '''Read current archive entry contents into string.'''
        return _libarchive.archive_read_data_into_str(self._a, size)

    def readpath(self, f):
        '''Write current archive entry contents to file. f can be a file-like object or
        a path.'''
        if isinstance(f, basestring):
            f = file(f, 'w')
        fd = fd.fileno()
        ret = _libarchive.archive_read_data_into_fd(self._a, fd)

    def readstream(self, size):
        '''Returns a file-like object for reading current archive entry contents.'''
        return EntryReadStream(size, self.read)

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
        member = self.entry_class.from_file(f, encoding=encoding)
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

    def writestream(self, pathname):
        '''Returns a file-like object for writing a new entry.'''
        return EntryWriteStream(pathname, self.write)


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
        self.close();
        self.f.seek(0)
        self.open()

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
        # Pass base read method to avoid calling into SeekableArchive.read()
        return EntryReadStream(entry.size, super(SeekableArchive, self).read)

