AUTOMAKE_OPTIONS = foreign
SUBDIRS = src

check:
	+./scripts/smoketest.py

examples: all
	+(cd examples && make)

