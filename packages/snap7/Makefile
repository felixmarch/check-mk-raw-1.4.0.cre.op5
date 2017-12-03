include ../../Makefile.omd

# This package contains the SNAP 7 library (http://snap7.sourceforge.net/)
# and also the related python bindings (https://pypi.python.org/pypi/python-snap7/).

NAME     = snap7
VERSION  = 1.3.0
DIR      = snap7-full-$(VERSION)
PYTHON   = LD_LIBRARY_PATH=$(shell pwd)/../python/tmp.python27/lib \
	   $(shell pwd)/../python/tmp.python27/bin/python

PY_VERSION = master
PY_DIR     = python-snap7-$(PY_VERSION)

ARCH = $(shell uname -m)
ifeq ($(ARCH),i686)
    ARCH=i386
endif

.PHONY: skel

build: check-python
	tar xzf $(DIR).tar.gz
	cd $(DIR)/build/unix && $(MAKE) -f $(ARCH)_linux.mk
	
	# Now handle the python module
	unzip -o $(PY_DIR).zip
	
	set -e ; for p in python-patches/*.dif ; do \
	echo "applying $$p..." ; \
	    patch -d $(PY_DIR) -p1 < $$p ; \
	done

check-python:
	@if [ ! -d ../python/tmp.python27 ]; then \
	    echo "ERROR: You need to build the \"python\" package first" ; \
	    exit 1 ; \
	fi

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib
	install -m 644 $(DIR)/build/bin/$(ARCH)-linux/libsnap7.so $(DESTDIR)$(OMD_ROOT)/lib
	
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/python && \
	export PYTHONPATH=$$PYTHONPATH:$(TMP_INSTALL_PATH)/lib ; \
	export PYTHONPATH=$$PYTHONPATH:$(DESTDIR)$(OMD_ROOT)/lib/python ; \
	export PYTHONPATH=$$PYTHONPATH:$(shell pwd)/../python/tmp.python27/lib/python2.7 ; \
	cd $(PY_DIR) && \
	$(PYTHON) setup.py install --home=$(DESTDIR)$(OMD_ROOT) \
	    --prefix='' \
	    --install-platlib=$(DESTDIR)$(OMD_ROOT)/lib/python \
	    --install-purelib=$(DESTDIR)$(OMD_ROOT)/lib/python

skel:

clean:
	rm -rf $(DIR) $(PY_DIR)
