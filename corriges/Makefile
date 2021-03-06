# -*- coding: utf-8 -*-

# particularly for the degree sign (was pdflatex)
LATEX = xelatex

all: everything

COURSEDIR = ../../flotpython-course

TOOL = makecorriges.py

TITLE = MOOC Python 3;Session 2018;Tous les corrigés
define title
MOOC Python 3;Session 2018;Corrigés de la semaine $(1)
endef
shipdict_title = MOOC Python 3;Session 2018;Exercice shipdict

WEEKS = 2 3 4 5 6 7
SHIPDICT-FILES = $(COURSEDIR)/data/shipdict.py
ALL = 2 3 4 5 $(SHIPDICT-FILES) 6 7

##########
# Semaine 6:
# un seul gros exo est proposé; on donne un morceau de code
# et il faut écrire le module manquant
# la soluce complète est dans data/shipdict.py
# qui contient pour des raisons historiques des balises BEG/END

shipdict: corriges-shipdict.tex

corriges-shipdict.tex:
	$(TOOL) --title "$(shipdict_title)" --output corriges-shipdict $(SHIPDICT-FILES)

pdf:: corriges-shipdict.pdf

##########
# the default for runcorriges is to produce both a .txt and .tex
WTEXS =  $(foreach week, $(WEEKS), corriges-w$(week).tex)

everything: corriges-all.tex $(WTEXS) shipdict

corriges-all.tex: .FORCE
	$(TOOL) --contents --title "$(TITLE)" --output corriges-all $(ALL)

pdf:: corriges-all.pdf

index:
	pdflatex corriges-all



###### how to redo a week
define week_target
w$(1): corriges-w$(1).tex

corriges-w$(1).tex: .FORCE
	$(TOOL) --output corriges-w$(1) \
	    --title "MOOC Python 3;Session 2018;Corrigés de la semaine $(1)" $(1)

corriges-w$(1).pdf: corriges-w$(1).tex
	$(LATEX) corriges-w$(1).tex

pdf:: corriges-w$(1).pdf
endef

$(foreach week, $(WEEKS), $(eval $(call week_target,$(week))))


########## validation
# convenience to generate a notebook fragment
# that can validate all known exos at once
validation:
	$(TOOL) --notebook -o validation $(WEEKS)

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
