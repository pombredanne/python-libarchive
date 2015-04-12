# Installing libarchive #

Many Linux distributions include libarchive 2. This extension only works with libarchive 3. In these cases, you must install libarchive to a /usr/local. This will allow it to co-exist with the version installed with your distribution. To install libarchive using autoconf, follow the instructions below.

**Prerequisites.**

You will need either automake or cmake to install libarchive. Also required is python-dev. In addition, you will also need a compiler and some other tools. To install these prerequisites do the following:

On Debian/Ubuntu:

```
# Install compiler and tools
$ sudo apt-get install build-essential libtool python-dev

# Install automake
$ sudo apt-get install automake

# Or install cmake
$ sudo apt-get install cmake
```

Or CentOS/Fedora:

```
# Install compiler and tools
$ sudo yum groupinstall "Development Tools"
$ sudo yum install python-devel libtool

# Install automake
$ sudo yum install automake

# Or install cmake
$ sudo yum install cmake
```

You should now be able to install libarchive.

```
$ wget http://libarchive.googlecode.com/files/libarchive-3.0.3.tar.gz
$ tar xzf libarchive-3.0.3.tar.gz

# Configure using automake...
$ cd libarchive-3.0.3/
$ build/autogen.sh
$ ./configure --prefix=/usr/local

# Or configure using cmake...
$ mkdir build
$ cd build
$ cmake -DCMAKE_INSTALL_PREFIX=/usr/local ../libarchive-3.0.3

# Now compile and install...
$ make
$ sudo make install
```

Now that the library is installed, you need to tell ld where to find it. The easiest way to do this is to add /usr/local/lib to the ld.so.conf.

```
$ sudo sh -c 'echo /usr/local/lib > /etc/ld.so.conf.d/libarchive3.conf'
$ sudo ldconfig
```

Now libarchive 3.0.3 is installed into /usr/local/. The next step is to build and install python-libarchive.

# Installing python-libarchive #

Now that libarchive is installed, you can install the python extension using the steps below.

```
$ wget http://python-libarchive.googlecode.com/files/python-libarchive-3.0.3-2.tar.gz
$ tar xzf python-libarchive-3.0.3-2.tar.gz
$ cd python-libarchive-3.0.3-2/
$ sudo python setup.py install
```

You can also install using pip.

```
$ pip install python-libarchive
```

setup.py will explicitly link against version 3.0.3 of the library.

# Hacking / Running the Test Suite #

The test suite is located in the root directory. This is done purposefully to make hacking easier. If you make changes to the library, you can run the test suite against the local copy in the libarchive/ subdirectory rather than the version installed on your system.

However, this means you need to have the extension compiled in this same directory. You will also need SWIG for this step. You can accomplish this using the following commands.

On Debian/Ubuntu:

```
$ sudo apt-get install swig
```

Or CentOS/Fedora:

```
$ sudo yum install swig
```

Now you can re-SWIG the interface and recompile the extension.

```
$ cd libarchive/
$ make
$ cd ..
```

Now you can run the test suite from the main directory.

```
$ python tests.py
```