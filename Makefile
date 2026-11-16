# Makefile for BB-8 Buddy

PYTHON ?= python3
PREFIX ?= /usr/local

.PHONY: all run checkin dashboard test package install clean

all: test package

run:
	$(PYTHON) bin/bb8-buddy

checkin:
	$(PYTHON) bin/bb8-buddy --checkin

dashboard:
	$(PYTHON) bin/bb8-buddy --dashboard

test:
	$(PYTHON) tests/run_tests.py

package:
	./package-deb.sh

install:
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	mkdir -p $(DESTDIR)$(PREFIX)/lib/bb8-buddy
	mkdir -p $(DESTDIR)$(PREFIX)/share/applications
	mkdir -p $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps
	cp -r bb8_buddy ui assets $(DESTDIR)$(PREFIX)/lib/bb8-buddy/
	install -m 755 bin/bb8-buddy $(DESTDIR)$(PREFIX)/bin/bb8-buddy
	install -m 644 assets/bb8-buddy.desktop $(DESTDIR)$(PREFIX)/share/applications/
	install -m 644 assets/icons/bb8-buddy.svg $(DESTDIR)$(PREFIX)/share/icons/hicolor/scalable/apps/

clean:
	rm -rf build dist __pycache__ bb8_buddy/__pycache__ tests/__pycache__

