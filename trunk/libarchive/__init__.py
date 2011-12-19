import math, warnings
from libarchive import _libarchive

# Suggested block size for libarchive. It may adjust it.
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


class EOF(Exception):
    '''Raised by ArchiveInfo.__init__() when unable to read the next
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
    def __init__(self, archive):
        self._e = _libarchive.archive_entry_new()
        self.archive = archive
        tries = 0
        while True:
            tries += 1
            ret = _libarchive.archive_read_next_header2(self.archive._a, self._e)
            if ret == _libarchive.ARCHIVE_OK:
                break
            elif ret == _libarchive.ARCHIVE_WARN:
                warnings.warn(_libarchive.archive_error_string(self.archive._a), RuntimeWarning)
                break
            elif ret == _libarchive.ARCHIVE_EOF:
                raise EOF()
            elif ret in (_libarchive.ARCHIVE_FAILED, _libarchive.ARCHIVE_FATAL):
                raise Exception('Error reading archive entry. %s.' % self.archive.geterror())
            elif ret == _libarchive.ARCHIVE_RETRY:
                if tries > 3:
                    raise Exception('Error reading archive entry. %s. Failed after %s tries.' % (
                        self.archive.geterror(), tries))
                continue
        self.header_position = archive.header_position
        self.pathname = _libarchive.archive_entry_pathname_w(self._e)
        self.size = _libarchive.archive_entry_size(self._e)
        self.mtime = _libarchive.archive_entry_mtime(self._e)

    def __del__(self):
        _libarchive.archive_entry_free(self._e)


class Archive(object):
    '''A low-level archive reader which provides forward-only iteration. Consider
    this a light-weight pythonic libarchive wrapper.'''
    def __init__(self, f, mode='r', format=None, filter=None, entry_klass=Entry):
        assert mode in ('r', 'w', 'a'), 'Mode should be "r", "w", or "a".'
        self.entry_klass = entry_klass
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
                ret = _libarchive.archive_read_open_filename(self._a, f, BLOCK_SIZE)
            else:
                ret = _libarchive.archive_write_open_filename(self._a, f)
            if ret not in (_libarchive.ARCHIVE_WARN, _libarchive.ARCHIVE_OK):
                raise Exception('Error %s opening archive.' % ret)
        elif hasattr(f, 'fileno'):
            self._filePassed = 1
            self.filename = getattr(f, 'name', None)
            if self.mode == 'r':
                ret = _libarchive.archive_read_open_fd(self._a, f.fileno(), BLOCK_SIZE)
            else:
                ret = _libarchive.archive_write_open_fd(self._a, f.fileno())
            if ret not in (_libarchive.ARCHIVE_WARN, _libarchive.ARCHIVE_OK):
                raise Exception('Error %s opening archive.' % ret)
        else:
            raise Exception('Provided file is not path or open file.')

    def __iter__(self):
        while True:
            try:
                yield self.entry_klass(self)
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
        if self.mode == 'r':
            _libarchive.archive_read_close(self._a)
            _libarchive.archive_read_free(self._a)
        elif self.mode == 'w':
            _libarchive.archive_write_close(self._a)
            _libarchive.archive_write_free(self._a)

    @property
    def header_position(self):
        '''The position within the file.'''
        return _libarchive.archive_read_header_position(self._a)

    def copy(self, fd):
        '''Write current archive entry contents to file.'''
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        ret = _libarchive.archive_read_data_into_fd(self._a, fd)

    def read(self, size):
        '''Read current archive entry contents into string.'''
        return _libarchive.archive_read_data_into_str(self._a, size)

    def readfile(self, size):
        '''Returns a file-like object for reading current archive entry contents.'''
        return EntryStream(self, size)

    def geterror(self):
        '''Gets string for last error.'''
        return _libarchive.archive_error_string(self.archive._a)


class SeekableArchive(object):
    '''A class that provides random-access to archive entries. It does this by using one
    or many Archive instances to seek to the correct locations. The best performance will
    occur when reading archive entries in the order in which they appear in the archive.
    Reading out of order will cause the archive to be closed and opened each time a
    reverse seek is needed.'''
    def __init__(self, f, **kwargs):
        # Convert file to open file. We need this to reopen the archive.
        mode = kwargs.setdefault('mode', 'r')
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

    def readfile(self, member):
        '''Returns a file-like object for reading requested archive entry contents.'''
        entry = self.getentry(member)
        self.seek(entry)
        return self.archive.readfile(entry.size)


def test():
    import pdb; pdb.set_trace()
    #~ f = file('/tmp/tmpcXJbRE/test.zip', 'r')
    #~ a = _libarchive.archive_read_new()
    #~ _libarchive.archive_read_support_filter_all(a)
    #~ _libarchive.archive_read_support_format_all(a)
    #~ _libarchive.archive_read_open_fd(a, f.fileno(), 10240)
    #~ while True:
        #~ e = _libarchive.archive_entry_new()
        #~ r = _libarchive.archive_read_next_header2(a, e)
        #~ l = _libarchive.archive_entry_size(e)
        #~ s = _libarchive.archive_read_data_into_str(a, l)
        #~ _libarchive.archive_entry_free(e)
        #~ if r != _libarchive.ARCHIVE_OK:
            #~ break
    #~ _libarchive.archive_read_close(a)
    #~ _libarchive.archive_read_free(a)
    #~ a = _libarchive.archive_read_new()
    #~ _libarchive.archive_read_support_filter_all(a)
    #~ _libarchive.archive_read_support_format_all(a)
    #~ _libarchive.archive_read_open_fd(a, f.fileno(), 10240)
    #~ while True:
        #~ e = _libarchive.archive_entry_new()
        #~ r = _libarchive.archive_read_next_header2(a, e)
        #~ l = _libarchive.archive_entry_size(e)
        #~ s = _libarchive.archive_read_data_into_str(a, l)
        #~ _libarchive.archive_entry_free(e)
        #~ if r != _libarchive.ARCHIVE_OK:
            #~ break
    #~ _libarchive.archive_read_close(a)
    #~ _libarchive.archive_read_free(a)

    z = Archive('/tmp/tmpcXJbRE/test.zip')
    for entry in z:
        print entry.pathname
    #~ z = ArchiveFile('tests/test.zip')
    #~ print '1'
    #~ z.read('libarchive/Makefile')
    #~ print '2'
    #~ z.read('libarchive/_libarchive.i')

if __name__ == '__main__':
    test()
