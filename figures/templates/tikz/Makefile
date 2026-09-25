# Build every standalone TikZ template into ../../examples/tikz_<name>.{pdf,png}
#   make            # needs latexmk + pdflatex (TeX Live) and pdftoppm (poppler)
#   make clean
EX    ?= ../../examples
SRC   := $(wildcard *.tex)
PDFS  := $(SRC:%.tex=$(EX)/tikz_%.pdf)
PNGS  := $(PDFS:.pdf=.png)
LATEX ?= latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=build

all: $(PDFS) $(PNGS)

$(EX)/tikz_%.pdf: %.tex crypto-tikz.sty
	@mkdir -p $(EX) build
	$(LATEX) $< > build/$*.stdout 2>&1 || (tail -30 build/$*.log; false)
	cp build/$*.pdf $@

$(EX)/tikz_%.png: $(EX)/tikz_%.pdf
	pdftoppm -png -r 300 -singlefile $< $(basename $@)

clean:
	rm -rf build

.PHONY: all clean
