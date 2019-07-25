SHELL = /bin/bash

download-valgrind:
	cd .. && git clone --branch=$(VALGRIND_VERSION) --single-branch git://sourceware.org/git/valgrind.git valgrind+verrou >/dev/null

patch-valgrind:
	cd ../valgrind+verrou && cp -a $(PWD) verrou
	cd ../valgrind+verrou && patch -p1 <verrou/valgrind.diff
patch-error:
	cd ../valgrind+verrou && find . -name '*.rej' | xargs tail -n+1
	# try to build verrou anyway if we check the development version of Valgrind
	test "$(VALGRIND_VERSION)" = "master"

configure:
	cd ../valgrind+verrou && ./autogen.sh
	cd ../valgrind+verrou && ./configure --enable-only64bit --enable-verrou-fma=yes --prefix=$${PWD}/install

build:
	cd ../valgrind+verrou && make
	cd ../valgrind+verrou && make install >/dev/null

check-install:
	source ../valgrind+verrou/install/env.sh && valgrind --version
	source ../valgrind+verrou/install/env.sh && valgrind --tool=verrou --help

check:
	cd ../valgrind+verrou && make -C tests  check
	cd ../valgrind+verrou && make -C verrou check
	cd ../valgrind+verrou && perl tests/vg_regtest verrou
	cd ../valgrind+verrou && make -C verrou/Interlibmath/testlibM/ check
check-error:
	cd ../valgrind+verrou/verrou/tests && tail -n+1 *.stdout.diff *.stdout.out *.stderr.diff *.stderr.out
	@false

unit-test:
	cd ../valgrind+verrou/verrou/unitTest && make
