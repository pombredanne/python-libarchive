CFLAGS     = -g
INCLUDE    = -I/usr/include -I.
LIBS       = -L/usr/lib64 -l:libarchive.so.11.0.1
#if PYTHON_VERSION
PYVER = $(PYTHON_VERSION)
#else
PYVER = 2.7
#endif
PYINCLUDE = -DHAVE_CONFIG_H -I/usr/include/python$(PYVER) \
            -I/usr/include/python$(PYVER)
PYLIB     = /usr/include/python$(PYVER)

all: _archive

_archive: _archive.i
	swig -python -shadow _archive.i
	cc -c -fpic $(CFLAGS) $(INCLUDE) $(PYINCLUDE) _archive_wrap.c
	ld -Bshareable -o __archive.so _archive_wrap.o $(LIBS) 

clean:
	rm -f *_wrap* *.o *.so _archive.py *.pyc
