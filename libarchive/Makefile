
all: _libarchive_wrap.c _libarchive.py

_libarchive_wrap.c _libarchive.py: _libarchive.i
	swig -python -shadow _libarchive.i

clean:
	rm -f _libarchive.py _libarchive_wrap.c
