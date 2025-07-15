# -*- coding: utf-8 -*-

# particularly for the degree sign (was pdflatex)
LATEX = xelatex

all: tex
.PHONY: all

COURSEDIR = ../../flotpython-course

TOOL = makecorriges.py

TITLE = MOOC Python 3;Tous les corrigés

##########
# Semaine 6:
# un seul gros exo est proposé; on donne un morceau de code
# et il faut écrire le module manquant
# la soluce complète est dans data/shipdict.py
# qui contient pour des raisons historiques des balises BEG/END

WEEKS = 2 3 4 5 6 7
SHIPDICT-FILES = $(COURSEDIR)/data/shipdict.py
ALL = 2 3 4 5 $(SHIPDICT-FILES) 6 7

##########
# the default for runcorriges is to produce both a .txt and .tex
WTEXS =  $(foreach week, $(WEEKS), corriges-w$(week).tex)

tex: corriges-all.tex

corriges-all.tex: .FORCE
	$(TOOL) --contents --title "$(TITLE)" --output corriges-all $(ALL)

pdf:: corriges-all.pdf

index:
	pdflatex corriges-all

.PHONY: tex pdf index


########## validation
# convenience to generate a notebook fragment
# that can validate all known exos at once
validation:
	$(TOOL) --notebook -o validation $(WEEKS)

.PHONY: validation

########## separate
# create one .py file per solution in the separate/ 
# directory so that individual solutions can be passed along
separate:
	$(TOOL) --separate $(WEEKS)
.PHONY: separate

##### boilerplate

%.pdf: %.tex
	$(LATEX) $*

.PHONY: all clean superclean pdf

clean:
	rm -f *.{aux,log,tex,toc,out}

superclean:
	rm -rf corriges-w* corriges-shipdict* separate/

.FORCE:

#################### convenience, for debugging only
# make +foo : prints the value of $(foo)
# make ++foo : idem but verbose, i.e. foo=$(foo)
++%: varname=$(subst +,,$@)
++%:
	@echo "$(varname)=$($(varname))"
+%: varname=$(subst +,,$@)
+%:
	@echo "$($(varname))"
