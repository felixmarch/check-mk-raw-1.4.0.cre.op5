include ../../Makefile.omd

NAME = rrdtool
VERSION = 1.5.4
DIR = $(NAME)-$(VERSION)
PYTHON = LD_LIBRARY_PATH=$(shell pwd)/../python/tmp.python27/lib \
	   $(shell pwd)/../python/tmp.python27/bin/python

CONFIGUREOPTS = \
	--prefix=$(OMD_ROOT) \
	--disable-ruby \
	--disable-libwrap \
	--enable-perl-site-install \
	--disable-tcl \
	--disable-lua \
	--disable-rrdcgi \
	--with-perl-options="LIB=$(DESTDIR)$(OMD_ROOT)/lib/perl5/lib/perl5"

build: check-python
	if [ -d $(DIR) ]; then rm -rf $(DIR); fi
	tar xzf $(DIR).tar.gz
	for p in patches/*.diff ; do \
          echo "applying $$p..." ; \
          patch -p1 -b -d $(DIR) < $$p ; \
        done

	# set perl environment to match the other perl modules
	echo "install  --install_base  $(DESTDIR)$(OMD_ROOT)/lib/perl5" > .modulebuildrc
# The MS_ASYNC/mtime check is broken and often leads to non-killable sync syscalls.
# Furthermore, the check doesn't make sense at all in a chroot environment.
	case "$$(lsb_release -i | cut -f2) $$(lsb_release -r | cut -f2)" in \
	  CentOS\ 5.*) MS_ASYNC=broken ;; \
	  *) MS_ASYNC=ok ;; \
	esac ; \
	export PERL5LIB=$(P5TMPDIST)/dest/lib/perl5:$$(pwd)/../perl-modules/dist/lib/perl5:$$(pwd)/../perl-modules/dist/lib/perl5/$(PERLARCH); \
        export PERL_MM_OPT=INSTALL_BASE=$(DESTDIR)$(OMD_ROOT)/lib/perl5; \
        export MODULEBUILDRC=$$(pwd)/.modulebuildrc; \
        export PKG_CONFIG_PATH="../../glib/glib-2.13.7:../../pango/pango-1.17.5:../../cairo/cairo-1.4.6/src"; \
        export top_builddir="."; \
	cd $(DIR) && \
	LDFLAGS="$(shell pkg-config --libs gthread-2.0) -lglib-2.0 -L$$(pwd)/../../cairo/cairo-1.4.6/src/.libs -L$$(pwd)/../../glib/glib-2.13.7/glib/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango/.libs -L$$(pwd)/../../pango/pango-1.17.5/pango" \
        CPPFLAGS="$(shell pkg-config --cflags gthread-2.0) -I$$(pwd)/../../glib/glib-2.13.7 -I$$(pwd)/../../glib/glib-2.13.7/glib -I$$(pwd)/../../pango/pango-1.17.5 -I$$(pwd)/../../pango/pango-1.17.5/pango -I$$(pwd)/../../cairo/cairo-1.4.6/src" \
	rd_cv_ms_async="$$MS_ASYNC" \
        ./configure $(CONFIGUREOPTS) && \
        $(MAKE) all

	# Python binding
	export LDFLAGS="-L$(shell pwd)/../python/tmp.python27/lib -L$(shell pwd)/../python/tmp.python27/lib/python2.7/config" ; \
	cd $(DIR)/bindings/python && $(PYTHON) setup.py build

check-python:
	@if [ ! -d ../python/tmp.python27 ]; then \
	    echo "ERROR: You need to build the \"python\" package first" ; \
	    exit 1 ; \
	fi

install:
	export PERL5LIB=$(P5TMPDIST)/dest/lib/perl5; \
	$(MAKE) DESTDIR=$(DESTDIR) -C $(DIR) install
	
	# clean up perl man pages which end up in wrong location
	# clean up systemd init files. Note that on RPM based distros this
	# seem to be located in /usr/lib and on debian /lib.
	if [ -n "$(DESTDIR)" ]; then \
	    rm -fr $(DESTDIR)/usr/local ; \
	    rm -fr $(DESTDIR)/usr/share ; \
	    rm -fr $(DESTDIR)/lib ; \
	    rm -fr $(DESTDIR)/usr/lib ; \
	fi
	
	mkdir $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool || true
	install -m 644 $(DIR)/COPYRIGHT $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool
	install -m 644 $(DIR)/CONTRIBUTORS $(DESTDIR)$(OMD_ROOT)/share/doc/rrdtool

	# Python binding
	export PYTHONPATH=$$PYTHONPATH:$(DESTDIR)$(OMD_ROOT)/lib/python && \
	cd $(DIR)/bindings/python && \
	    $(PYTHON) setup.py install --home=$(DESTDIR)/$(OMD_ROOT) --prefix "" \
		--install-platlib=$(DESTDIR)$(OMD_ROOT)/lib/python \
		--install-purelib=$(DESTDIR)$(OMD_ROOT)/lib/python \
	
	if [ -n "$(DESTDIR)$(OMD_ROOT)" -a -d "$(DESTDIR)$(OMD_ROOT)/lib64" ] ; then \
	    rsync -avh $(DESTDIR)$(OMD_ROOT)/lib64/* $(DESTDIR)$(OMD_ROOT)/lib/ ; \
	    rm -rf $(DESTDIR)$(OMD_ROOT)/lib64 ; \
	fi

skel:

clean:
	rm -rf $(DIR)
	rm -rf .modulebuildrc
