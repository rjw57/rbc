B_FILES:=$(wildcard *.b)
BEXPR_FILES:=$(wildcard *.bexpr)

GENERATED_DOT:=$(B_FILES:.b=.ast.dot) $(BEXPR_FILES:.bexpr=.ast.dot)

PYTHON?=python

all: $(GENERATED_DOT)

clean:
	rm -f $(GENERATED_DOT)

.PHONY: all clean

%.ast.dot: %.b
	$(PYTHON) -m rbc.dumpast --dot "$<" >"$@"

%.ast.dot: %.bexpr
	$(PYTHON) -m rbc.dumpast --dot -p expr "$<" >"$@"
