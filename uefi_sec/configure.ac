AC_PREREQ(2.61)
AC_INIT([cbsp-boot-utilities],1.0.0)
AM_INIT_AUTOMAKE([-Wall gnu foreign])
AM_MAINTAINER_MODE
AC_CONFIG_HEADERS([config.h])
AC_CONFIG_MACRO_DIR([m4])

AC_PROG_CC
AM_PROG_CC_C_O
AM_PROG_AR
AM_PROG_AS
AC_PROG_LIBTOOL
AC_PROG_AWK
AC_PROG_CPP
AC_PROG_INSTALL
AC_PROG_LN_S
AC_PROG_MAKE_SET
AC_PROG_CXX

PKG_PROG_PKG_CONFIG

PKG_CHECK_MODULES(GLIB, glib-2.0 >= 2.16, dummy=yes, AC_MSG_ERROR(GLib >= 2.16 is required))
GLIB_CFLAGS="$GLIB_CFLAGS"
GLIB_LIBS="$GLIB_LIBS"
AC_SUBST(GLIB_CFLAGS)
AC_SUBST(GLIB_LIBS)

AC_ARG_WITH(systemdunitdir,
        AC_HELP_STRING([--with-systemdunitdir=DIR],
        [Path of systemd unit directory @<:@default=LIBDIR/systemd/system@:>@]),
        [path_systemdunit=$withval],
        [path_systemdunit="`$PKG_CONFIG --variable=systemdsystemunitdir systemd`"])

if (test -n "${path_systemdunit}"); then
        SYSTEMD_UNITDIR="${path_systemdunit}"
        AC_SUBST(SYSTEMD_UNITDIR)
fi
AM_CONDITIONAL(USE_SYSTEMD, test -n "${path_systemdunit}")

AC_CONFIG_FILES([Makefile])

LT_INIT
AC_OUTPUT
