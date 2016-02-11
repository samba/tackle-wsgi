
PACKAGE:=tackle
VERSION_PATTERN = "^[0-9]+\.[0-9]+\.[0-9]+$$"

GIT_BRANCH = $(shell git describe --contains --all HEAD)
GIT_COMMIT = $(shell git log -1 "--pretty=format:%H")
GIT_STATUS = $(shell git status -sb --untracked=no | wc -l | awk '{ if($$1 == 1){ print "clean" } else { print "pending" } }')

DRYRUN ?= true 

ifeq ($(DRYRUN),false)
	DRYRUN=
else
	DRYRUN=--dry-run
endif


.PHONY: install clean uninstall build upload test git-status-clean

clean:
	rm -vf release-version 

git-status-clean:
	test "${GIT_STATUS}" == "clean" || (echo "GIT STATUS NOT CLEAN"; exit 1) >&2

install:
	sudo python setup.py check install

remove uninstall:
	sudo pip uninstall ${PACKAGE}

build: git-status-clean
	python setup.py check build 

upload: build
	python setup.py ${DRYRUN} build sdist bdist upload


release-version: git-status-clean
	python -c "from tackle import __version__; print __version__"  > $@
	git tag `cat $@`
