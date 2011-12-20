#!/usr/bin/env python
# coding=utf-8

import os, unittest, tempfile, random, string, subprocess

from libarchive.zip import ZipFile, ZipEntry

TMPDIR = tempfile.mkdtemp()
ZIPCMD = '/usr/bin/zip'
ZIPFILE = 'test.zip'
ZIPPATH = os.path.join(TMPDIR, ZIPFILE)

FILENAMES = [
    'test1.txt',
    'foo',
    # TODO: test non-ASCII chars.
    #'álért.txt',
]

def make_temp_files():
    print TMPDIR
    if not os.path.exists(ZIPPATH):
        for name in FILENAMES:
            file(os.path.join(TMPDIR, name), 'w').write(''.join(random.sample(string.printable, 10)))

def make_temp_archive():
    if not os.access(ZIPCMD, os.X_OK):
        raise AssertionError('Cannot execute %s.' % ZIPCMD)
    cmd = [ZIPCMD, ZIPFILE]
    make_temp_files()
    cmd.extend(FILENAMES)
    os.chdir(TMPDIR)
    subprocess.call(cmd)

class TestZipRead(unittest.TestCase):
    def setUp(self):
        make_temp_archive()

    def test_iterate(self):
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
        count = 0
        for e in z:
            count += 1
        self.assertEqual(count, len(FILENAMES), 'Did not enumerate correct number of items in archive.')

    def test_filenames(self):
        f = file(ZIPPATH, mode='r')
        z = ZipFile(f, 'r')
        names = []
        for e in z:
            names.append(e.filename)
        self.assertEqual(names, FILENAMES, 'File names differ in archive.')

    #~ def test_non_ascii(self):
        #~ pass

    def test_extract_str(self):
        pass


class TestZipWrite(unittest.TestCase):
    def setUp(self):
        make_temp_files()

    def test_create(self):
        f = file(ZIPPATH, mode='w')
        z = ZipFile(f, 'w')
        for fname in FILENAMES:
            e = ZipEntry(fname)
            z.writepath(e, file(os.path.join(TMPDIR, fname), 'r'))
        z.close()

if __name__ == '__main__':
    unittest.main()