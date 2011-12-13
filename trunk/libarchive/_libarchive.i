%module _libarchive

%{
#include <archive.h>
#include <archive_entry.h>
%}

%include "typemaps.i"

# Everything below is from the archive.h and archive_entry.h files.
# I excluded functions declarations that are not needed.

/* CONFIGURATION */

#include <sys/types.h>
#include <stddef.h>  /* for wchar_t */
#include <time.h>

#if defined(_WIN32) && !defined(__CYGWIN__)
#include <windows.h>
#endif

/* Get appropriate definitions of standard POSIX-style types. */
/* These should match the types used in 'struct stat' */
#if defined(_WIN32) && !defined(__CYGWIN__)
#define	__LA_INT64_T	__int64
# if defined(__BORLANDC__)
#  define	__LA_UID_T	uid_t  /* Remove in libarchive 3.2 */
#  define	__LA_GID_T	gid_t  /* Remove in libarchive 3.2 */
#  define	__LA_DEV_T	dev_t
#  define	__LA_MODE_T	mode_t
# else
#  define	__LA_UID_T	short  /* Remove in libarchive 3.2 */
#  define	__LA_GID_T	short  /* Remove in libarchive 3.2 */
#  define	__LA_DEV_T	unsigned int
#  define	__LA_MODE_T	unsigned short
# endif
#else
#include <unistd.h>
# if defined(_SCO_DS)
#  define	__LA_INT64_T	long long
# else
#  define	__LA_INT64_T	int64_t
# endif
# define	__LA_UID_T	uid_t /* Remove in libarchive 3.2 */
# define	__LA_GID_T	gid_t /* Remove in libarchive 3.2 */
# define	__LA_DEV_T	dev_t
# define	__LA_MODE_T	mode_t
#endif

/*
 * Remove this for libarchive 3.2, since ino_t is no longer used.
 */
#define	__LA_INO_T	ino_t


/*
 * On Windows, define LIBARCHIVE_STATIC if you're building or using a
 * .lib.  The default here assumes you're building a DLL.  Only
 * libarchive source should ever define __LIBARCHIVE_BUILD.
 */
#if ((defined __WIN32__) || (defined _WIN32) || defined(__CYGWIN__)) && (!defined LIBARCHIVE_STATIC)
# ifdef __LIBARCHIVE_BUILD
#  ifdef __GNUC__
#   define extern	__attribute__((dllexport)) extern
#  else
#   define extern	__declspec(dllexport)
#  endif
# else
#  ifdef __GNUC__
#   define extern
#  else
#   define extern	__declspec(dllimport)
#  endif
# endif
#else
/* Static libraries on all platforms and shared libraries on non-Windows. */
# define extern
#endif

/* STRUCTURES */
struct archive;
struct archive_entry;

/* ARCHIVE READING */
extern struct archive	*archive_read_new(void);
extern int		 archive_read_free(struct archive *);

/* opening */
extern int archive_read_open_filename(struct archive *,
		     const char *_filename, size_t _block_size);
extern int archive_read_open_memory(struct archive *,
		     void * buff, size_t size);
extern int archive_read_open_memory2(struct archive *a, void *buff,
		     size_t size, size_t read_size);
extern int archive_read_open_fd(struct archive *, int _fd,
		     size_t _block_size);

/* closing */
extern int		 archive_read_close(struct archive *);

/* headers */
int archive_read_next_header2(struct archive *,
		     struct archive_entry *);

/* data */
extern __LA_SSIZE_T		 archive_read_data(struct archive *,
				    void *, size_t);
extern int archive_read_data_skip(struct archive *);
extern int archive_read_data_into_buffer(struct archive *,
			    void *buffer, __LA_SSIZE_T len);
extern int archive_read_data_into_fd(struct archive *, int fd);

/* FILTERS */
extern int archive_read_support_filter_all(struct archive *);
extern int archive_read_support_filter_bzip2(struct archive *);
extern int archive_read_support_filter_compress(struct archive *);
extern int archive_read_support_filter_gzip(struct archive *);
extern int archive_read_support_filter_lzip(struct archive *);
extern int archive_read_support_filter_lzma(struct archive *);
extern int archive_read_support_filter_none(struct archive *);
extern int archive_read_support_filter_rpm(struct archive *);
extern int archive_read_support_filter_uu(struct archive *);
extern int archive_read_support_filter_xz(struct archive *);

/* FORMATS */
extern int archive_read_support_format_all(struct archive *);
extern int archive_read_support_format_7zip(struct archive *);
extern int archive_read_support_format_ar(struct archive *);
extern int archive_read_support_format_cab(struct archive *);
extern int archive_read_support_format_cpio(struct archive *);
extern int archive_read_support_format_empty(struct archive *);
extern int archive_read_support_format_gnutar(struct archive *);
extern int archive_read_support_format_iso9660(struct archive *);
extern int archive_read_support_format_lha(struct archive *);
extern int archive_read_support_format_mtree(struct archive *);
extern int archive_read_support_format_rar(struct archive *);
extern int archive_read_support_format_raw(struct archive *);
extern int archive_read_support_format_tar(struct archive *);
extern int archive_read_support_format_xar(struct archive *);
extern int archive_read_support_format_zip(struct archive *);

/* ARCHIVE WRITING */
extern struct archive	*archive_write_new(void);
extern int		 archive_write_free(struct archive *);

/* opening */
extern int archive_write_open(struct archive *, void *,
		     archive_open_callback *, archive_write_callback *,
		     archive_close_callback *);
extern int archive_write_open_fd(struct archive *, int _fd);
extern int archive_write_open_filename(struct archive *, const char *_file);
extern int archive_write_open_filename_w(struct archive *,
		     const wchar_t *_file);
extern int archive_write_open_memory(struct archive *,
			void *_buffer, size_t _buffSize, size_t *_used);

/* closing */
extern int		 archive_write_close(struct archive *);

/* headers */
extern int archive_write_header(struct archive *,
		     struct archive_entry *);

/* data */
extern __LA_SSIZE_T	archive_write_data(struct archive *,
			    const void *, size_t);

/* commit */
extern int		 archive_write_finish_entry(struct archive *);

/* FILTERS */
extern int archive_write_add_filter_bzip2(struct archive *);
extern int archive_write_add_filter_compress(struct archive *);
extern int archive_write_add_filter_gzip(struct archive *);
extern int archive_write_add_filter_lzip(struct archive *);
extern int archive_write_add_filter_lzma(struct archive *);
extern int archive_write_add_filter_none(struct archive *);
extern int archive_write_add_filter_xz(struct archive *);


/* FORMATS */
/* A convenience function to set the format based on the code or name. */
extern int archive_write_set_format(struct archive *, int format_code);
extern int archive_write_set_format_by_name(struct archive *,
		     const char *name);
/* To minimize link pollution, use one or more of the following. */
extern int archive_write_set_format_ar_bsd(struct archive *);
extern int archive_write_set_format_ar_svr4(struct archive *);
extern int archive_write_set_format_cpio(struct archive *);
extern int archive_write_set_format_cpio_newc(struct archive *);
extern int archive_write_set_format_gnutar(struct archive *);
extern int archive_write_set_format_iso9660(struct archive *);
extern int archive_write_set_format_mtree(struct archive *);
/* TODO: int archive_write_set_format_old_tar(struct archive *); */
extern int archive_write_set_format_pax(struct archive *);
extern int archive_write_set_format_pax_restricted(struct archive *);
extern int archive_write_set_format_shar(struct archive *);
extern int archive_write_set_format_shar_dump(struct archive *);
extern int archive_write_set_format_ustar(struct archive *);
extern int archive_write_set_format_xar(struct archive *);
extern int archive_write_set_format_zip(struct archive *);

/* ARCHIVE ENTRY */
extern struct archive_entry	*archive_entry_new(void);
extern void			 archive_entry_free(struct archive_entry *);

/* ARCHIVE ENTRY PROPERTY ACCESS */
/* reading */
extern const char	*archive_entry_pathname(struct archive_entry *);
extern __LA_INT64_T	 archive_entry_size(struct archive_entry *);
extern time_t	 archive_entry_mtime(struct archive_entry *);

/* writing */
extern void	archive_entry_set_pathname(struct archive_entry *, const char *);
extern void	archive_entry_set_size(struct archive_entry *, __LA_INT64_T);
extern void	archive_entry_set_mtime(struct archive_entry *, time_t, long);


/* CONSTANTS */
#define	ARCHIVE_VERSION_NUMBER 3000001
#define	ARCHIVE_VERSION_STRING "libarchive 3.0.1b"
#define	ARCHIVE_EOF	  1	/* Found end of archive. */
#define	ARCHIVE_OK	  0	/* Operation was successful. */
#define	ARCHIVE_RETRY	(-10)	/* Retry might succeed. */
#define	ARCHIVE_WARN	(-20)	/* Partial success. */
#define	ARCHIVE_FAILED	(-25)	/* Current operation cannot complete. */
#define	ARCHIVE_FATAL	(-30)	/* No more operations are possible. */

#define	ARCHIVE_FILTER_NONE	0
#define	ARCHIVE_FILTER_GZIP	1
#define	ARCHIVE_FILTER_BZIP2	2
#define	ARCHIVE_FILTER_COMPRESS	3
#define	ARCHIVE_FILTER_PROGRAM	4
#define	ARCHIVE_FILTER_LZMA	5
#define	ARCHIVE_FILTER_XZ	6
#define	ARCHIVE_FILTER_UU	7
#define	ARCHIVE_FILTER_RPM	8
#define	ARCHIVE_FILTER_LZIP	9

#define	ARCHIVE_FORMAT_BASE_MASK		0xff0000
#define	ARCHIVE_FORMAT_CPIO			0x10000
#define	ARCHIVE_FORMAT_CPIO_POSIX		(ARCHIVE_FORMAT_CPIO | 1)
#define	ARCHIVE_FORMAT_CPIO_BIN_LE		(ARCHIVE_FORMAT_CPIO | 2)
#define	ARCHIVE_FORMAT_CPIO_BIN_BE		(ARCHIVE_FORMAT_CPIO | 3)
#define	ARCHIVE_FORMAT_CPIO_SVR4_NOCRC		(ARCHIVE_FORMAT_CPIO | 4)
#define	ARCHIVE_FORMAT_CPIO_SVR4_CRC		(ARCHIVE_FORMAT_CPIO | 5)
#define	ARCHIVE_FORMAT_CPIO_AFIO_LARGE		(ARCHIVE_FORMAT_CPIO | 6)
#define	ARCHIVE_FORMAT_SHAR			0x20000
#define	ARCHIVE_FORMAT_SHAR_BASE		(ARCHIVE_FORMAT_SHAR | 1)
#define	ARCHIVE_FORMAT_SHAR_DUMP		(ARCHIVE_FORMAT_SHAR | 2)
#define	ARCHIVE_FORMAT_TAR			0x30000
#define	ARCHIVE_FORMAT_TAR_USTAR		(ARCHIVE_FORMAT_TAR | 1)
#define	ARCHIVE_FORMAT_TAR_PAX_INTERCHANGE	(ARCHIVE_FORMAT_TAR | 2)
#define	ARCHIVE_FORMAT_TAR_PAX_RESTRICTED	(ARCHIVE_FORMAT_TAR | 3)
#define	ARCHIVE_FORMAT_TAR_GNUTAR		(ARCHIVE_FORMAT_TAR | 4)
#define	ARCHIVE_FORMAT_ISO9660			0x40000
#define	ARCHIVE_FORMAT_ISO9660_ROCKRIDGE	(ARCHIVE_FORMAT_ISO9660 | 1)
#define	ARCHIVE_FORMAT_ZIP			0x50000
#define	ARCHIVE_FORMAT_EMPTY			0x60000
#define	ARCHIVE_FORMAT_AR			0x70000
#define	ARCHIVE_FORMAT_AR_GNU			(ARCHIVE_FORMAT_AR | 1)
#define	ARCHIVE_FORMAT_AR_BSD			(ARCHIVE_FORMAT_AR | 2)
#define	ARCHIVE_FORMAT_MTREE			0x80000
#define	ARCHIVE_FORMAT_RAW			0x90000
#define	ARCHIVE_FORMAT_XAR			0xA0000
#define	ARCHIVE_FORMAT_LHA			0xB0000
#define	ARCHIVE_FORMAT_CAB			0xC0000
#define	ARCHIVE_FORMAT_RAR			0xD0000
#define	ARCHIVE_FORMAT_7ZIP			0xE0000

#define	ARCHIVE_EXTRACT_OWNER			(0x0001)
#define	ARCHIVE_EXTRACT_PERM			(0x0002)
#define	ARCHIVE_EXTRACT_TIME			(0x0004)
#define	ARCHIVE_EXTRACT_NO_OVERWRITE 		(0x0008)
#define	ARCHIVE_EXTRACT_UNLINK			(0x0010)
#define	ARCHIVE_EXTRACT_ACL			(0x0020)
#define	ARCHIVE_EXTRACT_FFLAGS			(0x0040)
#define	ARCHIVE_EXTRACT_XATTR 			(0x0080)
#define	ARCHIVE_EXTRACT_SECURE_SYMLINKS		(0x0100)
#define	ARCHIVE_EXTRACT_SECURE_NODOTDOT		(0x0200)
#define	ARCHIVE_EXTRACT_NO_AUTODIR		(0x0400)
#define	ARCHIVE_EXTRACT_NO_OVERWRITE_NEWER	(0x0800)
#define	ARCHIVE_EXTRACT_SPARSE			(0x1000)
#define	ARCHIVE_EXTRACT_MAC_METADATA		(0x2000)
