# -*- coding: utf-8 -*-

all: everything

COURSEDIR = ../../flotpython-course

TOOL = runcorriges.py

TITLE = MOOC Python 3;Session 2018;Tous les corrigés
define title
MOOC Python 3;Session 2018;Corrigés de la semaine $(1)
endef

WEEKS = 2 3 4 5 7

##########
# Semaine 6:
# un seul gros exo est proposé; on donne un morceau de code
# et il faut écrire le module manquant
# la soluce complète est dans data/shipdict.py
# qui contient pour des raisons historiques des balises BEG/END
W6_FILES = $(COURSEDIR)/data/shipdict.py

w6: corriges-w6.tex

corriges-w6.tex:
	$(TOOL) --title "$(call title, 6)" --output corriges-w6 $(W6_FILES)

pdf:: corriges-w6.pdf

##########
# the default for runcorriges is to produce both a .txt and .tex
WTEXS =  $(foreach week, $(WEEKS), corriges-w$(week).tex)

everything: corriges-all.tex $(WTEXS)

corriges-all.tex: .FORCE
	$(TOOL) --contents --title "$(TITLE)" --output corriges-all $(WEEKS)

pdf:: corriges-all.pdf


###### how to redo a week
define week_target
w$(1): corriges-w$(1).tex

corriges-w$(1).tex: .FORCE
	$(TOOL) --output corriges-w$(1) \
	    --title "MOOC Python 3;Session 2018;Corrigés de la semaine $(1)" $(1)

corriges-w$(1).pdf: corriges-w$(1).tex
	pdflatex corriges-w$(1).tex

pdf:: corriges-w$(1).pdf
endef

$(foreach week, $(WEEKS), $(eval $(call week_target,$(week))))


########## validation
# convenience to generate a notebook fragment
# that can validate all known exos at once
validation:
	$(TOOL) --notebook -o $(COURSEDIR)/modules/corrections/validation $(WEEKS)

##### boilerplate

%.pdf: %.tex
	pdflatex $*

.PHONY: all clean superclean pdf

clean:
	rm -f *.{aux,log,tex,toc,out}

superclean:
	rm -rf corriges-w*

index:
	for tex in *.tex; do pdflatex $$tex; done

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
