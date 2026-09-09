# ============================================================
# Makefile — VPN Access Manager
# Builds two PDFs into out/:
#   user-manual     end-user documentation
#   developer-doc   developer documentation
# Adapted from the DBMS_10 course Makefile (THGA Bochum).
# ============================================================

LATEXMK  := latexmk
OUTDIR   := out

LMKFLAGS := -pdf -interaction=nonstopmode -halt-on-error \
            -cd -output-directory=../$(OUTDIR)

TEXENV   := TEXINPUTS="$(CURDIR)/style:.:$$TEXINPUTS"
STYLE    := style/thga-db.sty

vpath %.tex docs

DOCS     := user-manual developer-doc
ALL_PDF  := $(addprefix $(OUTDIR)/, $(addsuffix .pdf, $(DOCS)))

.PHONY: all clean distclean help
all: $(ALL_PDF)

$(OUTDIR):
	mkdir -p $(OUTDIR)

$(OUTDIR)/%.pdf: %.tex $(STYLE) | $(OUTDIR)
	$(TEXENV) $(LATEXMK) $(LMKFLAGS) $<

clean:
	rm -f $(addprefix $(OUTDIR)/, *.aux *.log *.fdb_latexmk *.fls *.out *.toc *.synctex.gz)

distclean:
	rm -rf $(OUTDIR)

help:
	@echo "  all        – build both PDFs (→ $(OUTDIR)/)"
	@echo "  clean      – remove auxiliary files, keep PDFs"
	@echo "  distclean  – remove everything including $(OUTDIR)/"
