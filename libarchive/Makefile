CFLAGS     = -g
INCLUDE    = -I/usr/include -I.
LIBS       = -L/usr/lib64 -l:libarchive.so.11.0.1

#if PYTHON_VERSION
PYVER = $(PYTHON_VERSION)
#else
PYVER = 2.7
#endif

all: __libarchive.so

_libarchive_wrap.c: _libarchive.i
	swig -python -shadow _libarchive.i

_libarchive_wrap.o: _libarchive_wrap.c
	${CC} -c ${CFLAGS} -fPIC ${INCLUDE} $$(python${PYVER}-config --cflags) _libarchive_wrap.c

__libarchive.so: _libarchive_wrap.o
	${CC} _libarchive_wrap.o -shared $$(python${PYVER}-config --ldflags) -o __libarchive.so ${LIBS}

clean:
	rm -f *_wrap* *.o *.so _libarchive.py *.pyc
