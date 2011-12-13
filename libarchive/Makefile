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

all: _libarchive

_libarchive: _libarchive.i
	swig -python -shadow _libarchive.i
	cc -c -fpic $(CFLAGS) $(INCLUDE) $(PYINCLUDE) _libarchive_wrap.c
	ld -Bshareable -o __libarchive.so _libarchive_wrap.o $(LIBS) 

clean:
	rm -f *_wrap* *.o *.so _libarchive.py *.pyc
