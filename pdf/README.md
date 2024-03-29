# HOW TO

## Update Nov 2023

- turns out that a recent jupytext somehow decided to drop tags in `latex:` because of the `:`
- so we are renaming all these tags into `latex-` in both
  - the notebook master sources in flotpython-tools
  - the local tool `nbcustomexec.py`

- this time we obtain `Python-w1-to-w7.pdf` that is `5783306` bytes large, and so it cannot be uploaded...

## Update July 2023

hopefuly the last one...

* due to space limitations, the complete pdf covers
  only the first 7 weeks

* about svg insertion
  * ~~uninstall the Inkspace app (if present)~~ this seems conter-productive in fact
  * use `brew install inkscape` to install the command-line tool
  * result is not perfect at all, but it's kind of OK:
    * ~~there remains the need to manually remove the `.png` extensions within the calls to `\includesvg`~~ this is now taken care of by `convert-one`
    *  (only 2 notebooks, and 4 figures)

## Update May 2020

I took some time to move to a more recent version of nbconvert

* this involved patching `Python.tex` from the output of a mundane  
  `jupyter nbconvert --to latex`  
  I tried to keep this input separate from our local changes

**THIS IS NOT RESOLVED**  

Another problem with inclusion of `.svg` files - that are not natively supported with
latex (they have no boundingbox); this issue turned out to be a gigantic waste of time

* could not make it with using the {svg} package :
  * requires to run `xelatex` with the `--shell-escape` option
  * requires separate (and non-trivial) installation of InkScape
  * that in turn requires patching PATH
  * and with all this in place it seems like inkscape now has a new command-line
    interface, and so `includesvg` just won't work as is
* have also seen references to a Python `cairosvg` package
  * that I could install through `pip install`
  * but that could not load due to a allegedly unknown locale `UTF-8`

So because we only have 4 figures of that sort for now I am just giving up for today.

## Warning:

Historically, I just wanted to ignore a textual output entirely.
However, that primarily never flew.

So. Some day Fangh started to produce pdf on his own; that paved the way, but it
was tedious too, so at some point I came up with something to do it
automatically, so it could be done over and over again.

## The idea

Workflow can be sketched like this:
* execute the notebooks using a customized nbconvert preprocessor
* run nbconvert to produce latex
* use a hand-crafted umbrella `Python.tex`, that was initially produced by
  nbconvert but, later on heavily patched upon by Fangh - thanks again for that:)
* select actual weeks, inject resulting tex in the mix,
* and run with `pdflatex`

## Caveats

It's not perfect, but it's OK.

Here's a - probably not exhaustive - list of things that work, how they work,
and of things that still could use ironing.

#### Chapter names

At some point we need to define names for the various chapters; this is
currently written manually in a totally *ad hoc* format in
`ChapterNames.txt`.

#### Special tags in cell metadata

We have defined a few cell metadata keys that allow us to work around most
issues as we ran into them:

* `latex-skip-cell` : ignore that cell altogether: don't evaluate,
   don't show in output;
* `latex-skip-eval` : don't evaluate that cell, but keep in output;
* `latex-hidden-code-instead` : this is for cells that expect an input,
  typically with builtin `input()`; we run this code instead of the actual cell
  code;
* `latex-hidden-silent` : resulting cell code just says something odd has
  happened, but does not divulge actual code; typically in conjunction with
  `latex-hidden-code-instead` for exercises;
* `latex-replace` : allows to replace parts of the source; typically used to
  deal with characters that were not supported by latex.

**Notes**

* these keys are to be used as **raw metadata**, and *not* as tags (remember a
  metadata tag cannot have a value); in cases where a boolean value is expected
  (e.g. `latex-skip-cell`), only the presence of the key is checked, regardless
  of the associated value
* there's also provisions for
  * `latex-hidden-code-before` and
  * `latex-hidden-code-after`  
     but I did not need these eventually
* `latex-replace` was kind of convenient, but it's still a little hacky:
  * first off it does not replace in the cell's outputs - for now, at least;
  * second, this way of dealing with weird symbols turned out a huge waste
    of time; at some point I thought I'd have more power with xelatex
    instead of pdflatex, but then some other parts stopped working as well,
    so after a while I decided I did not care too much about these - very
    few - places that needed attention, as long as the latex step runs fine.

#### Remaining known issues

* **URLs:** Fangh suggests using proper links when inserting a URL; inserting a
  URL as-is works in the web, but results in a poor pdf output.

## Workflow

* get the list of available notebooks
* each of them goes through `nbcustomexec.py`, that outputs a copy locally here
  under `work/name.ipynb`
* run `nbconvert --to latex` to produce `work/name.tex`
* run `striplatex.py` to keep just valuable contents, between `\begin{document}`
  and `\end{document}`
* run `scopecontents.py` that overwrites `contents.tex` according to the weeks
  of interest

* finally process `Python.tex` as usual - several times, that is, to get the
  page numbering right.

All this is for now only partially automated. Here are a few hints:

#### preparation

*  define this to point at your main course repo

```
export COURSEDIR=$HOME/git/flotpython-course
export TOOLSDIR=$HOME/git/flotpython-tools
```

* prepare work area & symlinks

```
mkdir -p work
for symlink in media data; do
    ln -sf $COURSEDIR/$symlink work
done
```

*****

*****

#### load tools utilities

This file is at the root of the flotpython-tools repo

```bash
source ../bashrc-utils
```

#### execute notebook_names

```bash
execute-all
```

This command will recompute all executed notebooks;

* it does this lazily (compares modification times)
* WARNING: this will **not** remove old stuff in case of a renaming
* its safe to trash `work` altogether in case of doubt; it takes a few minutes
  to recompute the whole stuff though.

#### convert to $\LaTeX$

**note** make sure to remove all nbclassic-related stuff
```
pip uninstall jupyter-contrib-nbextensions jupyter-nbextensions-configurator widgetsnbextension
```

```bash
convert-all
```

Likewise:

* does this lazily by comparing modification times,
* this will actually run a pipeline of `nbconvert --to latex` and `striplatex.py`,
* the latter being in charge of
  * (a) removing extra header and footer stuff, and
  * (b) tweaking the output to suit our aesthetic tastes.

#### shortcut

```bash
prepare-all
```

just does `execute-all` + `convert-all`

#### selecting scope - in weeks

```bash
scopecontents.py
# or
scopecontents.py 1 5
# or
scopecontents.py --from 1 --to 6
```

#### rebuild

with the config chosen above with scopecontents.py , rebuild the pdf

```bash
latex-current
```

Run several times (twice should be enough, 3 times to be safe) - as always, to get cross references - like table of contents - right.

#### doing PDFs

```bash
week 6
```

which would recompute the following files - stored in `pdf/` and not in `work/`:

* `Python-w6.pdf`,

```bash
week-one-to 6
```

computes
* `Python-w1-to-w6.pdf`,

```bash
redo-all-pdfs
```

will redo all 9 weeks and w1-to-w9
