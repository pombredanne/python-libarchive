import time, math
from libarchive import _libarchive
from zipfile import ZIP_STORED, ZIP_DEFLATED

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
            elif ret == _libarchive.ARCHIVE_EOF:
                raise EOF()
            elif ret in (_libarchive.ARCHIVE_FAILED, _libarchive.ARCHIVE_FATAL):
                raise Exception('Error %s reading archive entries.' % ret)
            elif ret == _libarchive.ARCHIVE_RETRY:
                if tries > 3:
                    raise Exception('Error reading archive entries. Failed after %s tries.' % tries)
                continue
        self.header_position = archive.header_position
        self.pathname = _libarchive.archive_entry_pathname(self._e)
        self.size = _libarchive.archive_entry_size(self._e)
        self.mtime = _libarchive.archive_entry_mtime(self._e)

    def __del__(self):
        _libarchive.archive_entry_free(self._e)


class Archive(object):
    '''A low-level archive reader which provides forward-only iteration. Consider
    this a light-weight pythonic libarchive wrapper.'''
    info_klass = Entry

    def __init__(self, f, mode='r', format=None, filter=None):
        assert mode in ('r', 'w', 'a'), 'Mode should be "r", "w", or "a".'
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
                yield self.info_klass(self)
            except EOF:
                break

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __del__(self):
        self.close()

    def close(self):
        if self.mode == 'r':
            _libarchive.archive_read_close(self._a)
            _libarchive.archive_read_free(self._a)
        elif self.mode == 'w':
            _libarchive.archive_write_close(self._a)
            _libarchive.archive_write_free(self._a)

    @property
    def header_position(self):
        return _libarchive.archive_read_header_position(self._a)

    def read_to_file(self, fd):
        if hasattr(fd, 'fileno'):
            fd = fd.fileno()
        ret = _libarchive.archive_read_data_into_fd(self._a, fd)

    def read(self, size):
        return _libarchive.archive_read_data_into_str(self._a, size)


class ArchiveFile(object):
    '''A class that provides random-access to archive entries. It does this by using one
    or many Archive instances to seek to the correct locations. The best performance will
    occur when reading archive entries in the order in which they appear in the file.
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
        self._open()

    def _open(self):
        self.f.seek(0)
        self.archive = Archive(self.f, **self.archive_kwargs)

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

    def read(self, member):
        if isinstance(member, basestring):
            # Caller passed a name, so find the entry:
            for entry in self:
                if entry.pathname == member:
                    break
        else:
            # Caller passed an entry, assume it is correct and
            # originally came from us.
            entry = member
        # determine which way to move.
        move = entry.header_position - self.archive.header_position
        if move != 0:
            if move < 0:
                # can't move back, re-open archive:
                self._open()
            # move to proper position in stream
            for curr in self.archive:
                if curr.header_position == entry.header_position:
                    break
        # Extract entry.
        return self.archive.read(entry.size)

    def extract(self, entry):
        pass


#~ class ZipInfo(ArchiveInfo):
    #~ # Rename for compatibility with zipfile.ZipInfo
    #~ filename = ArchiveInfo.pathname
    #~ file_size = ArchiveInfo.size
    #~ date_time = ArchiveInfo.mtime

    #~ def _get_missing(self):
        #~ raise NotImplemented()

    #~ def _set_missing(self, value):
        #~ raise NotImplemented()

    #~ compress_type = property(_get_missing, _set_missing)
    #~ comment = property(_get_missing, _set_missing)
    #~ extra = property(_get_missing, _set_missing)
    #~ create_system = property(_get_missing, _set_missing)
    #~ create_version = property(_get_missing, _set_missing)
    #~ extract_version = property(_get_missing, _set_missing)
    #~ reserved = property(_get_missing, _set_missing)
    #~ flag_bits = property(_get_missing, _set_missing)
    #~ volume = property(_get_missing, _set_missing)
    #~ internal_attr = property(_get_missing, _set_missing)
    #~ external_attr = property(_get_missing, _set_missing)
    #~ header_offset = property(_get_missing, _set_missing)
    #~ CRC = property(_get_missing, _set_missing)
    #~ compress_size = property(_get_missing, _set_missing)


#~ class ZipFile(ArchiveFile):
    #~ info_klass = ZipInfo

    #~ def __init__(self, file, mode='r', compression=ZIP_DEFLATED, allowZip64=False):
        #~ assert compression in (ZIP_STORED, ZIP_DEFLATED), 'Requested compression is not supported.'
        #~ if compression == ZIP_STORED:
            #~ pass # TODO: ensure this disables compression.
        #~ elif compression == ZIP_DEFLATED:
            #~ pass # TODO: ensure this enables compression.
        #~ super(ZipFile, self).__init__(file, mode, format='zip')

    #~ def setpassword(self, pwd):
        #~ raise NotImplemented()

    #~ def testzip(self):
        #~ raise NotImplemented()

    #~ def _get_comment(self):
        #~ raise NotImplemented()

    #~ def _set_comment(self, comment):
        #~ raise NotImplemented()

    #~ comment = property(_get_comment, _set_comment)


#~ class TarInfo(ArchiveInfo):
    #~ name = ArchiveInfo.pathname


#~ class TarFile(ArchiveFile):
    #~ info_klass = TarInfo

    #~ def __init__(self, file, mode='r', fileobj=None):
        #~ if fileobj is not None:
            #~ file = fileobj
        #~ super(ZipFile, self).__init__(file, mode, format='tar')

    #~ getmember = ArchiveFile.getinfo
    #~ getmembers = ArchiveFile.infolist
    #~ getnames = ArchiveFile.namelist
    #~ list = ArchiveFile.printdir

    #~ def next(self):
        #~ try:
            #~ return self.info_klass(self)
        #~ except EOF:
            #~ pass


def test():
    import pdb; pdb.set_trace()
    f = file('tests/test.zip', 'r')
    a = _libarchive.archive_read_new()
    _libarchive.archive_read_support_filter_all(a)
    _libarchive.archive_read_support_format_all(a)
    _libarchive.archive_read_open_fd(a, f.fileno(), 10240)
    while True:
        e = _libarchive.archive_entry_new()
        r = _libarchive.archive_read_next_header2(a, e)
        l = _libarchive.archive_entry_size(e)
        s = _libarchive.archive_read_data_into_str(a, l)
        _libarchive.archive_entry_free(e)
        if r != _libarchive.ARCHIVE_OK:
            break
    _libarchive.archive_read_close(a)
    _libarchive.archive_read_free(a)
    a = _libarchive.archive_read_new()
    _libarchive.archive_read_support_filter_all(a)
    _libarchive.archive_read_support_format_all(a)
    _libarchive.archive_read_open_fd(a, f.fileno(), 10240)
    while True:
        e = _libarchive.archive_entry_new()
        r = _libarchive.archive_read_next_header2(a, e)
        l = _libarchive.archive_entry_size(e)
        s = _libarchive.archive_read_data_into_str(a, l)
        _libarchive.archive_entry_free(e)
        if r != _libarchive.ARCHIVE_OK:
            break
    _libarchive.archive_read_close(a)
    _libarchive.archive_read_free(a)

    z = Archive('tests/test.zip')
    for entry in z:
        print entry.pathname
    z = ArchiveFile('tests/test.zip')
    print '1'
    z.read('libarchive/Makefile')
    print '2'
    z.read('libarchive/_libarchive.i')

if __name__ == '__main__':
    test()
