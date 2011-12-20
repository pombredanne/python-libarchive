import time
from libarchive import Entry, SeekableArchive
from zipfile import ZIP_STORED, ZIP_DEFLATED

ENTRY_ATTR_MAP = (
    ('filename', 'pathname'),
    ('file_size', 'size'),
    ('date_time', 'mtime'),
)

class ZipEntry(Entry):
    def __init__(self, *args, **kwargs):
        super(ZipEntry, self).__init__(*args, **kwargs)
        for l, r in ENTRY_ATTR_MAP:
            setattr(self, l, getattr(self, r))
            delattr(self, r)
        self.date_time = time.localtime(self.date_time)[0:6]

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


class ZipFile(SeekableArchive):
    def __init__(self, f, mode='r', compression=ZIP_DEFLATED, allowZip64=False):
        super(ZipFile, self).__init__(f, mode=mode, format='zip', entry_klass=ZipEntry)
        if mode == 'w' and compression == ZIP_STORED:
            # Disable compression for writing.
            _libarchive.archive_write_set_format_option(self.archive._a, "zip", "compression", "store")

    def setpassword(self, pwd):
        raise NotImplemented()

    def testzip(self):
        raise NotImplemented()

    def _get_comment(self):
        raise NotImplemented()

    def _set_comment(self, comment):
        raise NotImplemented()

    comment = property(_get_comment, _set_comment)
