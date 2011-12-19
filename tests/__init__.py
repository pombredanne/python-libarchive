#!/usr/bin/env python
# coding=utf-8

import os, unittest, tempfile, random, string, subprocess

from libarchive.zip import ZipFile

TMPDIR = tempfile.mkdtemp()
ZIPCMD = '/usr/bin/zip'
ZIPFILE = 'test.zip'
ZIPPATH = os.path.join(TMPDIR, ZIPFILE)

FILENAMES = (
    'test1.txt',
    'foo',
    'álért.txt',
)

class TestZip(unittest.TestCase):
    def setUp(self):
        if not os.path.exists(ZIPPATH):
            if not os.access(ZIPCMD, os.X_OK):
                raise AssertionError('Cannot execute %s.' % ZIPCMD)
            cmd = [ZIPCMD, ZIPFILE]
            for name in FILENAMES:
                file(os.path.join(TMPDIR, name), 'w').write(''.join(random.sample(string.printable, 10)))
                cmd.append(name)
            os.chdir(TMPDIR)
            print TMPDIR, cmd
            subprocess.call(cmd)

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
        print names
        self.assertEqual(names, FILENAMES, 'File names differ in archive.')

    def test_non_ascii(self):
        pass

    def test_extract_str(self):
        pass


if __name__ == '__main__':
    unittest.main()