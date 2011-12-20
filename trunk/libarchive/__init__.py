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

import os, math, warnings, stat
from libarchive import _libarchive

# Suggested block size for libarchive. Libarchive may adjust it.
BLOCK_SIZE = 10240

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


class EntryStream(object):
    '''A file-like object for reading an entry from the archive.'''
    def __init__(self, archive, size):
        self.archive = archive
        self.size = size
        self.bytes = 0

    def read(self, bytes):
        if self.bytes == self.size:
            # EOF already reached.
            return
        if self.bytes + bytes > self.size:
            # Limit read to remaining bytes
            bytes = self.size - self.bytes
        # Read requested bytes
        data = self.archive.read(bytes)
        self.bytes += len(data)
        return data


class Entry(object):
    '''An entry within an archive. Represents the header data and it's location within the archive.'''
    def __init__(self, pathname=None, size=None, mtime=None, mode=None, hpos=None):
        self.pathname = pathname
        self.size = size
        self.mtime = mtime
        self.mode = mode
        self.hpos = hpos

    @property
    def header_position(self):
        return self.hpos

    @classmethod
    def from_archive(cls, archive):
        '''Instantiates an Entry class and sets all the properties from an archive header.'''
        e = _libarchive.archive_entry_new()
        try:
            exec_and_check(_libarchive.archive_read_next_header2, archive._a, archive._a, e)
            mode = _libarchive.archive_entry_filetype(e)
            mode |= _libarchive.archive_entry_perm(e)
            entry = cls(
                pathname = _libarchive.archive_entry_pathname(e),
                size = _libarchive.archive_entry_size(e),
                mtime = _libarchive.archive_entry_mtime(e),
                mode = mode,
                hpos = archive.header_position,
            )
        finally:
            _libarchive.archive_entry_free(e)
        return entry

    @classmethod
    def from_file(cls, f, entry=None):
        '''Instantiates an Entry class and sets all the properties from a file on the file system.
        f can be a file-like object or a path.'''
        if entry is None:
            entry = cls()
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
            _libarchive.archive_entry_set_pathname(e, self.pathname)
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
    def __init__(self, f, mode='r', format=None, filter=None, entry_class=Entry):
        assert mode in ('r', 'w', 'a'), 'Mode should be "r", "w", or "a".'
        self.entry_class = entry_class
        self.mode = mode
        formats = FORMATS.get(format, None)
        filters = FILTERS.get(filter, None)
        if self.mode == 'r':
            if formats is None:
                raise Exception('Unsupported format %s' % format)
            if filters is None:
                raise Exception('Unsupported filter %s' % filter)
            self._a = _libarchive.archive_read_new()
            formats[0](self._a)
            filters[0](self._a)
        else:
            # TODO: how to support appending?
            if formats is None:
                raise Exception('Unsupported format %s' % format)
            if filters is None:
                raise Exception('Unsupported filter %s' % filter)
            if formats[1] is None:
                raise Exception('Cannot write specified format.')
            self._a = _libarchive.archive_write_new()
            formats[1](self._a)
            filters[1](self._a)
        if isinstance(f, basestring):
            self._filePassed = 0
            self.filename = f
            if self.mode == 'r':
                exec_and_check(_libarchive.archive_read_open_filename, self._a, self._a, f, BLOCK_SIZE)
            else:
                exec_and_check(_libarchive.archive_write_open_filename, self._a, self._a, f)
        elif hasattr(f, 'fileno'):
            self._filePassed = 1
            self.filename = getattr(f, 'name', None)
            if self.mode == 'r':
                exec_and_check(_libarchive.archive_read_open_fd, self._a, self._a, f.fileno(), BLOCK_SIZE)
            else:
                exec_and_check(_libarchive.archive_write_open_fd, self._a, self._a, f.fileno())
        else:
            raise Exception('Provided file is not path or open file.')

    def __iter__(self):
        while True:
            try:
                yield self.entry_class.from_archive(self)
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
        return EntryStream(self, size)

    def write(self, entry, data):
        '''Writes a string buffer to the archive as the given entry.'''
        entry.size = len(data)
        entry.to_archive(self)
        _libarchive.archive_write_data_from_str(self._a, data)
        _libarchive.archive_write_finish_entry(self._a)

    def writepath(self, entry, f):
        '''Writes a file to the archive. f can be a file-like object or a path. Uses
        write() to do the actual writing.'''
        if isinstance(f, basestring):
            f = file(f, 'r')
        entry = self.entry_class.from_file(f)
        # TODO: optimize this path to write directly from f to archive.
        self.write(entry, f.read())


class SeekableArchive(object):
    '''A class that provides random-access to archive entries. It does this by using one
    or many Archive instances to seek to the correct location. The best performance will
    occur when reading archive entries in the order in which they appear in the archive.
    Reading out of order will cause the archive to be closed and opened each time a
    reverse seek is needed.'''
    def __init__(self, f, **kwargs):
        # Convert file to open file. We need this to reopen the archive.
        mode = kwargs.setdefault('mode', 'r')
        self.entry_class = kwargs.get('entry_class', Entry)
        if isinstance(f, basestring):
            f = file(f, mode)
        self.f = f
        self.archive_kwargs = kwargs
        self.entries_complete = False
        self.entries = []
        self.open()

    def __iter__(self):
        for entry in self.entries:
            yield entry
        if not self.entries_complete:
            try:
                for entry in self.archive:
                    self.entries.append(entry)
                    yield entry
            except EOF:
                self.entries_complete = True

    def open(self):
        '''Seeks the underlying fd to 0 position, then opens the archive. If the archive
        is already open, this will effectively re-open it (rewind to the beginning).'''
        self.f.seek(0)
        self.archive = Archive(self.f, **self.archive_kwargs)

    def getentry(self, name):
        '''Take a name or entry object and returns an entry object.'''
        if isinstance(member, basestring):
            # Caller passed a name, so find the entry:
            for entry in self:
                if entry.pathname == member:
                    return entry
        else:
            # Caller passed an entry, assume it is correct and
            # originally came from us.
            return member
        raise KeyError('no entry by that name')

    def seek(self, entry):
        '''Seeks the archive to the requested entry. Will reopen if necessary.'''
        move = entry.header_position - self.archive.header_position
        if move != 0:
            if move < 0:
                # can't move back, re-open archive:
                self.open()
            # move to proper position in stream
            for curr in self.archive:
                if curr.header_position == entry.header_position:
                    break

    def copy(self, member, fd):
        '''Write the requested archive entry contents to the given fd.'''
        entry = self.getentry(member)
        self.seek(entry)
        return self.archive.read(fd)

    def read(self, member):
        '''Return the requested archive entry contents as a string.'''
        entry = self.getentry(member)
        self.seek(entry)
        return self.archive.read(entry.size)

    def readpath(self, member, f):
        entry = self.getentry(member)
        self.seek(entry)
        return self.archive.readpath(f)

    def readstream(self, member):
        '''Returns a file-like object for reading requested archive entry contents.'''
        entry = self.getentry(member)
        self.seek(entry)
        return self.archive.readstream(entry.size)

    def write(self, member, data):
        '''Writes a string buffer to the archive as the given entry.'''
        if isinstance(member, basestring):
            member = self.entry_class(pathname=member)
        return self.archive.write(member, data)

    def writepath(self, member, f):
        '''Writes a file to the archive. f can be a file-like object or a path. Uses
        write() to do the actual writing.'''
        if isinstance(member, basestring):
            member = self.entry_class(pathname=member)
        return self.archive.writepath(member, f)

    def close(self):
        self.archive.close()
