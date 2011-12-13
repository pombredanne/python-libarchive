import time
import _libarchive
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


class ArchiveEOF(Exception):
    '''Raised by ArchiveInfo.__init__() when unable to read the next
    archive header.'''
    pass


class ArchiveInfo(object):
    def __init__(self, archive):
        self._libarchive = archive
        self._e = _libarchive.archive_entry_new()
        tries = 0
        while True:
            tries += 1
            ret = _libarchive.archive_read_next_header2(self._libarchive._a, self._e)
            if ret == _libarchive.ARCHIVE_OK:
                break
            elif ret == _libarchive.ARCHIVE_EOF:
                raise ArchiveEOF()
            elif ret in (_libarchive.ARCHIVE_FAILED, _libarchive.ARCHIVE_FATAL):
                raise Exception('Error %s reading archive entries.' % ret)
            elif ret == _libarchive.ARCHIVE_RETRY:
                if tries > 3:
                    raise Exception('Error reading archive entries. Failed after %s tries.' % tries)
                continue

    def __del__(self):
        _libarchive.archive_entry_free(self._e)

    def _get_pathname(self):
        return _libarchive.archive_entry_pathname(self._e)

    def _set_pathname(self, pathname):
        assert isinstance(pathname, basestring), 'Please provide pathname as string.'
        assert self._libarchive.mode != 'r', 'Cannot set pathname in read mode.'
        r = _libarchive.archive_entry_set_pathname(self._e, pathname)

    pathname = property(_get_pathname, _set_pathname)

    def _get_size(self):
        return _libarchive.archive_entry_size(self._e)

    def _set_size(self, size):
        assert isinstance(size, (int, long)), 'Please provide size as int or long.'
        assert self._libarchive.mode != 'r', 'Cannot set size in read mode.'
        r = _libarchive.archive_entry_set_size(self._e, size)

    size = property(_get_size, _set_size)

    def _get_mtime(self):
        date_time = _libarchive.archive_entry_mtime(self._e)
        date_time = time.localtime(date_time)
        return date_time[0:6]

    def _set_mtime(self, mtime):
        assert isinstance(mtime, tuple), 'mtime should be tuple (year, month, day, hour, minute, second).'
        assert len(mtime) == 6, 'mtime should be tuple (year, month, day, hour, minute, second).'
        assert self._libarchive.mode != 'r', 'Cannot set mtime in read mode.'
        mtime = time.mktime(mtime + (0, 0, 0))
        _libarchive.archive_entry_set_mtime(self._e, mtime)

    mtime = property(_get_mtime, _set_mtime)


class ArchiveFile(object):
    info_klass = ArchiveInfo

    def __init__(self, file, mode='r', format=None, filter=None):
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
        if isinstance(file, basestring):
            self._filePassed = 0
            self.filename = file
            if self.mode == 'r':
                ret = _libarchive.archive_read_open_filename(self._a, file, BLOCK_SIZE)
            else:
                ret = _libarchive.archive_write_open_filename(self._a, file)
            if ret not in (_libarchive.ARCHIVE_WARN, _libarchive.ARCHIVE_OK):
                raise Exception('Error %s opening archive.' % ret)
        elif hasattr(file, 'fileno'):
            self._filePassed = 1
            self.filename = getattr(file, 'name', None)
            if self.mode == 'r':
                ret = _libarchive.archive_read_open_fd(self._a, file.fileno(), BLOCK_SIZE)
            else:
                ret = _libarchive.archive_write_open_fd(self._a, file.fileno())
            if ret not in (_libarchive.ARCHIVE_WARN, _libarchive.ARCHIVE_OK):
                raise Exception('Error %s opening archive.' % ret)
        else:
            raise Exception('Provided file is not path or open file.')

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
        else:
            _libarchive.archive_write_close(self._a)
            _libarchive.archive_write_free(self._a)

    def getinfo(self, name):
        for info in self.infolist():
            if info.pathname == name:
                return info

    def infolist(self):
        while True:
            try:
                yield self.info_klass(self)
            except ArchiveEOF:
                break

    def namelist(self):
        for info in self.infolist():
            yield info.pathname

    def open(self, name, mode, pwd):
        pass

    def extract(self, name, path, pwd):
        pass

    def extractall(self, path, names, pwd):
        pass

    def write(self, path, name, compression):
        pass

    def writestr(self, info_or_name, bytes, compression):
        pass

    def printdir(self):
        pass


class ZipInfo(ArchiveInfo):
    # Rename for compatibility with zipfile.ZipInfo
    filename = ArchiveInfo.pathname
    file_size = ArchiveInfo.size
    date_time = ArchiveInfo.mtime

    def _get_missing(self):
        raise NotImplemented()

    def _set_missing(self, value):
        raise NotImplemented()

    compress_type = property(_get_missing, _set_missing)
    comment = property(_get_missing, _set_missing)
    extra = property(_get_missing, _set_missing)
    create_system = property(_get_missing, _set_missing)
    create_version = property(_get_missing, _set_missing)
    extract_version = property(_get_missing, _set_missing)
    reserved = property(_get_missing, _set_missing)
    flag_bits = property(_get_missing, _set_missing)
    volume = property(_get_missing, _set_missing)
    internal_attr = property(_get_missing, _set_missing)
    external_attr = property(_get_missing, _set_missing)
    header_offset = property(_get_missing, _set_missing)
    CRC = property(_get_missing, _set_missing)
    compress_size = property(_get_missing, _set_missing)


class ZipFile(ArchiveFile):
    info_klass = ZipInfo

    def __init__(self, file, mode='r', compression=ZIP_DEFLATED, allowZip64=False):
        assert compression in (ZIP_STORED, ZIP_DEFLATED), 'Requested compression is not supported.'
        if compression == ZIP_STORED:
            pass # TODO: ensure this disables compression.
        elif compression == ZIP_DEFLATED:
            pass # TODO: ensure this enables compression.
        super(ZipFile, self).__init__(file, mode, format='zip')

    def setpassword(self, pwd):
        raise NotImplemented()

    def testzip(self):
        raise NotImplemented()

    def _get_comment(self):
        raise NotImplemented()

    def _set_comment(self, comment):
        raise NotImplemented()

    comment = property(_get_comment, _set_comment)


class TarInfo(ArchiveInfo):
    name = ArchiveInfo.pathname


class TarFile(ArchiveFile):
    info_klass = TarInfo

    def __init__(self, file, mode='r', fileobj=None):
        if fileobj is not None:
            file = fileobj
        super(ZipFile, self).__init__(file, mode, format='tar')

    getmember = ArchiveFile.getinfo
    getmembers = ArchiveFile.infolist
    getnames = ArchiveFile.namelist
    list = ArchiveFile.printdir

    def next(self):
        try:
            return self.info_klass(self)
        except ArchiveEOF:
            pass


def test():
    import pdb; pdb.set_trace()
    #~ a = _libarchive.archive_read_new()
    #~ _libarchive.archive_read_support_filter_all(a)
    #~ _libarchive.archive_read_support_format_all(a)
    #~ _libarchive.archive_read_open_filename(a, "tests/test.tar.gz", 10240)
    #~ e = _libarchive.archive_entry_new()
    #~ while True:
        #~ ret = _libarchive.archive_read_next_header2(a, e)
        #~ if ret != 0:
            #~ break
        #~ print _libarchive.archive_entry_pathname(e)
    #~ _libarchive.archive_read_free(a)

    z = ZipFile('tests/test.zip')
    print [e.file_name for e in z.infolist()]

if __name__ == '__main__':
    test()
