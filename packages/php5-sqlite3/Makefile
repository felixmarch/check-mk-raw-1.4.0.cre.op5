include ../../Makefile.omd

NAME     = php5-sqlite3
VERSION  = 5.1.2
DIR      = php-$(VERSION)

MODULE_DIR=lib
ifeq ($(shell uname -m),x86_64)
  MODULE_DIR=lib64
endif

.PHONY: skel

build:
	tar xzf php-$(VERSION).tar.gz
	cd $(DIR) && ./configure --enable-pdo=shared --with-sqlite=shared --with-pdo-sqlite=shared
	cd $(DIR) && $(MAKE)

install:
	mkdir -p $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	install -m 644 $(DIR)/modules/pdo.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	install -m 644 $(DIR)/modules/pdo_sqlite.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	install -m 644 $(DIR)/modules/sqlite.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	# php does not support several extension_dir options and we can not add our .so files to
	# the global paths. So link the needed extensions to our extension dir and make use of that
	# extension directory in our php instances.
	ln -s /usr/$(MODULE_DIR)/php5/extensions/gd.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	ln -s /usr/$(MODULE_DIR)/php5/extensions/iconv.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	ln -s /usr/$(MODULE_DIR)/php5/extensions/mbstring.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	ln -s /usr/$(MODULE_DIR)/php5/extensions/mcrypt.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	ln -s /usr/$(MODULE_DIR)/php5/extensions/sockets.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions
	ln -s /usr/$(MODULE_DIR)/php5/extensions/zlib.so $(DESTDIR)$(OMD_ROOT)/lib/php5/extensions

skel:
	# Assumes that the apache-omd package already createed the $(SKEL)/etc/apache/php.ini file
	# Simply change the extensions dir and ensure the pdo_sqlite extension is loaded
	echo -e "\n\n; OMD OMD OMD OMD OMD OMD\n\nextension_dir = ###ROOT###/lib/php5/extensions\nextension=pdo_sqlite.so" >> $(SKEL)/etc/apache/php.ini

clean:
	rm -rf $(DIR)
