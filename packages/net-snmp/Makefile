include ../../Makefile.omd

NAME     = net-snmp
VERSION  = 734f855
DIR      = $(NAME)-$(VERSION)
PYTHON   = LD_LIBRARY_PATH=$(shell pwd)/../python/tmp.python27/lib \
	     $(shell pwd)/../python/tmp.python27/bin/python

.PHONY: skel

build: check-python
	tar xzf $(NAME)-$(VERSION).tar.gz
	set -e ; for p in patches/*.dif ; do \
	    echo "applying $$p..." ; \
	    patch -p1 -b -d $(DIR) < $$p ; \
	done
# Skip Perl-Modules because of build errors when MIB loading is disabled.
# Skip Python binding because we need to use our own python, see install target.
	cd $(DIR) && ./configure \
	    --enable-ipv6 \
	    --disable-agent \
	    --disable-snmptrapd-subagent \
	    --with-mibdirs="\$$HOME/local/share/snmp/mibs:$(OMD_ROOT)/share/snmp/mibs:/usr/share/snmp/mibs" \
	    --with-defaults \
	    --disable-scripts \
	    --prefix=$(OMD_ROOT) && make

install:
	cd $(DIR)/snmplib && make DESTDIR=$(DESTDIR) installlibs
	cd $(DIR)/apps && make DESTDIR=$(DESTDIR) installbin
	cd $(DIR)/man && make DESTDIR=$(DESTDIR) install
	mkdir -p $(DESTDIR)$(OMD_ROOT)/share/snmp/mibs
	cd $(DIR)/mibs && make DESTDIR=$(DESTDIR) mibsinstall
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python
	cd $(DIR)/python && \
	    export PYTHONPATH=$$PYTHONPATH:$(DESTDIR)$(OMD_ROOT)/lib/python ; \
	    export PYTHONPATH=$$PYTHONPATH:$(shell pwd)/../python/tmp.python27/lib/python2.7 ; \
	    export LDFLAGS="-L$(shell pwd)/../python/tmp.python27/lib -L$(shell pwd)/../python/tmp.python27/lib/python2.7/config" ; \
	    $(PYTHON) setup.py install --basedir=.. --home=$(DESTDIR)$(OMD_ROOT) \
	        --prefix='' \
	        --install-platlib=$(DESTDIR)$(OMD_ROOT)/lib/python \
	        --install-purelib=$(DESTDIR)$(OMD_ROOT)/lib/python

check-python:
	@if [ ! -d ../python/tmp.python27 ]; then \
	    echo "ERROR: You need to build the \"python\" package first" ; \
	    exit 1 ; \
	fi

skel:

clean:
	rm -rf $(DIR)
