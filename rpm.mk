PWD ?= $(shell pwd)
RPMBUILD ?= $(PWD)/rpmbuild
RPM_VERSION ?= $(shell $(PWD)/rpm/rpmverrel.sh version)
RPM_RELEASE ?= $(shell $(PWD)/rpm/rpmverrel.sh release)
VERSION_PREREL ?= $(shell $(PWD)/rpm/rpmverrel.sh prerel)
RPM_VERSION_PREREL ?= $(shell $(PWD)/rpm/rpmverrel.sh prerel | sed -e 's/\./-/')
PACKAGE = 389-ds-base
RPM_NAME_VERSION = $(PACKAGE)-$(RPM_VERSION)$(RPM_VERSION_PREREL)
NAME_VERSION = $(PACKAGE)-$(RPM_VERSION)$(VERSION_PREREL)
TARBALL = $(NAME_VERSION).tar.bz2
NUNC_STANS_ON = 1
JEMALLOC_URL ?= $(shell rpmspec -P $(RPMBUILD)/SPECS/389-ds-base.spec | awk '/^Source3:/ {print $$2}')
JEMALLOC_TARBALL ?= $(shell basename "$(JEMALLOC_URL)")
BUNDLE_JEMALLOC = 1
NODE_MODULES_TEST = src/cockpit/389-console/node_modules/webpack
GIT_TAG = ${TAG}

# Some sanitizers are supported only by clang
CLANG_ON = 0
# Address Sanitizer
ASAN_ON = 0
# Memory Sanitizer (clang only)
MSAN_ON = 0
# Thread Sanitizer
TSAN_ON = 0
# Undefined Behaviour Sanitizer
UBSAN_ON = 0

RUST_ON = 0
PERL_ON = 1

clean:
	rm -rf dist
	rm -rf rpmbuild

install-node-modules:
	cd src/cockpit/389-console; make -f node_modules.mk install

build-cockpit: install-node-modules
	cd src/cockpit/389-console; make -f node_modules.mk build-cockpit-plugin

dist-bz2: install-node-modules
	cd src/cockpit/389-console; \
	rm -rf cockpit_dist; \
	make -f node_modules.mk build-cockpit-plugin; \
	mv node_modules node_modules.release; \
	touch cockpit_dist/*
	mkdir -p $(NODE_MODULES_TEST)
	touch -r src/cockpit/389-console/package.json $(NODE_MODULES_TEST)
	tar cjf $(GIT_TAG).tar.bz2 --transform "s,^,$(GIT_TAG)/," $$(git ls-files) src/cockpit/389-console/cockpit_dist/ src/cockpit/389-console/node_modules
	cd src/cockpit/389-console; \
	rm -rf node_modules; \
	mv node_modules.release node_modules

local-archive: build-cockpit
	-mkdir -p dist/$(NAME_VERSION)
	rsync -a --exclude=node_modules --exclude=dist --exclude=__pycache__ --exclude=.git --exclude=rpmbuild . dist/$(NAME_VERSION)

tarballs: local-archive
	-mkdir -p dist/sources
	cd dist; tar cfj sources/$(TARBALL) $(NAME_VERSION)
	cd src/cockpit/389-console; rm -rf dist
	rm -rf dist/$(NAME_VERSION)
	cd dist/sources ; \
	if [ $(BUNDLE_JEMALLOC) -eq 1 ]; then \
		wget $(JEMALLOC_URL) ; \
	fi

rpmroot:
	rm -rf $(RPMBUILD)
	mkdir -p $(RPMBUILD)/BUILD
	mkdir -p $(RPMBUILD)/RPMS
	mkdir -p $(RPMBUILD)/SOURCES
	mkdir -p $(RPMBUILD)/SPECS
	mkdir -p $(RPMBUILD)/SRPMS
	sed -e s/__VERSION__/$(RPM_VERSION)/ -e s/__RELEASE__/$(RPM_RELEASE)/ \
	-e s/__VERSION_PREREL__/$(VERSION_PREREL)/ \
	-e s/__NUNC_STANS_ON__/$(NUNC_STANS_ON)/ \
	-e s/__RUST_ON__/$(RUST_ON)/ \
	-e s/__ASAN_ON__/$(ASAN_ON)/ \
	-e s/__MSAN_ON__/$(MSAN_ON)/ \
	-e s/__TSAN_ON__/$(TSAN_ON)/ \
	-e s/__UBSAN_ON__/$(UBSAN_ON)/ \
	-e s/__PERL_ON__/$(PERL_ON)/ \
	-e s/__CLANG_ON__/$(CLANG_ON)/ \
	-e s/__BUNDLE_JEMALLOC__/$(BUNDLE_JEMALLOC)/ \
	rpm/$(PACKAGE).spec.in > $(RPMBUILD)/SPECS/$(PACKAGE).spec

rpmdistdir:
	mkdir -p dist/rpms

srpmdistdir:
	mkdir -p dist/srpms

rpmbuildprep:
	cp dist/sources/$(TARBALL) $(RPMBUILD)/SOURCES/
	cp rpm/$(PACKAGE)-* $(RPMBUILD)/SOURCES/
	if [ $(BUNDLE_JEMALLOC) -eq 1 ]; then \
		cp dist/sources/$(JEMALLOC_TARBALL) $(RPMBUILD)/SOURCES/ ; \
	fi

srpms: rpmroot srpmdistdir tarballs rpmbuildprep
	rpmbuild --define "_topdir $(RPMBUILD)" -bs $(RPMBUILD)/SPECS/$(PACKAGE).spec
	cp $(RPMBUILD)/SRPMS/$(RPM_NAME_VERSION)*.src.rpm dist/srpms/
	rm -rf $(RPMBUILD)

patch_srpms: rpmroot srpmdistdir tarballs rpmbuildprep
	cp rpm/*.patch $(RPMBUILD)/SOURCES/
	rpm/add_patches.sh rpm $(RPMBUILD)/SPECS/$(PACKAGE).spec
	rpmbuild --define "_topdir $(RPMBUILD)" -bs $(RPMBUILD)/SPECS/$(PACKAGE).spec
	cp $(RPMBUILD)/SRPMS/$(RPM_NAME_VERSION)*.src.rpm dist/srpms/
	rm -rf $(RPMBUILD)

rpms: rpmroot srpmdistdir rpmdistdir tarballs rpmbuildprep
	rpmbuild --define "_topdir $(RPMBUILD)" -ba $(RPMBUILD)/SPECS/$(PACKAGE).spec
	cp $(RPMBUILD)/RPMS/*/*$(RPM_VERSION)$(RPM_VERSION_PREREL)*.rpm dist/rpms/
	cp $(RPMBUILD)/SRPMS/$(RPM_NAME_VERSION)*.src.rpm dist/srpms/
	rm -rf $(RPMBUILD)

patch_rpms: rpmroot srpmdistdir rpmdistdir tarballs rpmbuildprep
	cp rpm/*.patch $(RPMBUILD)/SOURCES/
	rpm/add_patches.sh rpm $(RPMBUILD)/SPECS/$(PACKAGE).spec
	rpmbuild --define "_topdir $(RPMBUILD)" -ba $(RPMBUILD)/SPECS/$(PACKAGE).spec
	cp $(RPMBUILD)/RPMS/*/*$(RPM_VERSION)$(RPM_VERSION_PREREL)*.rpm dist/rpms/
	cp $(RPMBUILD)/SRPMS/$(RPM_NAME_VERSION)*.src.rpm dist/srpms/
	rm -rf $(RPMBUILD)
