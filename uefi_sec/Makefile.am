pkgconfigdir = $(libdir)/pkgconfig

AM_CFLAGS = -Wall -g \
        -Wundef \
        -Wstrict-prototypes \
        -Wno-trigraphs

ACLOCAL_AMFLAGS = -I m4

AM_CPPFLAGS = -D__packed__= \
    -DFEATURE_LE_DIAG \
    -DOE

bin_PROGRAMS = uefi_sec

uefi_sec_SOURCES = uefi_sec.c SecureUILib.h
uefi_sec_CPPFLAGS = $(AM_CPPFLAGS)
uefi_sec_CFLAGS = $(AM_CFLAGS)
uefi_sec_LDFLAGS = -lpthread -ldl -lQseeComApi -ldrmfs -lrpmb -lssd
uefi_sec_LDADD = -lQseeComApi -ldmabufheap -lqcbor -lminkdescriptor

if USE_SYSTEMD
systemdunitdir = @SYSTEMD_UNITDIR@
systemdunit_DATA = uefi_sec.service
endif
