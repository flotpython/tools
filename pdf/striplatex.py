#!/usr/bin/env python3

import sys
import re
from argparse import (ArgumentParser, ArgumentDefaultsHelpFormatter)

# this is where we put boxes around code cells
# as well as code included in the notebook with
# ```python
# some code
# ```
#
# note that with other ways to achieve the same effect, namely
# * code between ``` lines but without the python mention, or
# * code preceded with 4 spaces
# the resulting latex contains a plain \begin{verbatim}
# which is not as easily customizable

replacements = [

    # set all Verbatim (i.e. In[] and Out[]) with a colored frame
#    ('plain',
#     r'\begin{Verbatim}[commandchars=\\\{\}]',
#     r'\begin{Verbatim}[commandchars=\\\{\},frame=single,framerule=0.1mm,rulecolor=\color{cellframecolor}]'),

    # set all Highlighting (i.e. inserted code) with a colored frame
    ('plain',
     r'\begin{Highlighting}[]',
     r'\begin{Highlighting}[frame=lines,framerule=0.6mm,rulecolor=\color{asisframecolor}]'),

    # quick and dirty; use 'make' in the media/ subdir in course
    # so as to produce .png files for all .svg
    # that can then be included with a regular \includegraphics
    ('plain',
     r'.svg',
     r'.png'),

    # this is about removing an extra while line at the end of the
    # 'print' area for each code cell (mind you: not the Out: area)
    ('regex',
     r'(?m)[\n\s]+\\end\{Verbatim\}',
     '\n\\\\end{Verbatim}'),
 ]

def strip_latex(in_file, out_file, nbname):
    """
    Read from a file object, save in a file object

    Removes header and footer; adds a mention of the notebook name
    after the first section

    Idempotent
    """
    ignoring = True
    buffer = ""

    pattern = re.compile(r'w(?P<week>[0-9]+)-s(?P<seq>[0-9]+)')
    week, seq = pattern.match(nbname).groups()

    for line in in_file:
        if r'\begin{document}' in line:
            ignoring = False
            # define name only if we run this for the first time
            if '%%%' not in line:
                buffer += rf"\renewcommand{{\notebookname}}{{{nbname}}}" + "\n"
                buffer += rf"\renewcommand{{\notebookweek}}{{{week}}}" + "\n"
                buffer += rf"\renewcommand{{\notebookseq}}{{{seq}}}" + "\n"
            # for idempotency, i.e. so that we can run this
            # several times with no further changes
            buffer += r'%%%\begin{document}' + '\n'
            continue
        if r'\end{document}' in line:
            ignoring = True
            continue
        if r'\maketitle' in line:
            continue
        if r'Licence CC BY-NC-ND' in line:
            # xxx super patchy: when the licence includes more than the two
            # usual authors, the raw tex output can be something like
            # {Licence CC BY-NC-ND} {Thierry Parmentelat, Arnaud Legout \& Jean-Michel
            # Heras} {}
            # in which case we need to remove the extra lines
            opening = line.count('{')
            closing = line.count('}')
            # hopefully one more line is enough in this case
            if opening > closing:
                next(in_file)
            continue
        if not ignoring:
            buffer += line

    # apply replacements
    for mode, before, after in replacements:
        if mode == 'plain':
            buffer = buffer.replace(before, after)
        elif mode == 'regex':
            buffer = re.compile(before).sub(after, buffer)
        else:
            print(f'Unknown mode {mode} in replacements')

    out_file.write(buffer)


def main():
    parser = ArgumentParser(usage="redirect stdin and stdout as appropriate")
    parser.add_argument('-n', "--name", default='striplatex-name')
    args = parser.parse_args()

    strip_latex(sys.stdin, sys.stdout, args.name)

if __name__ == '__main__':
    main()
    exit(0)
