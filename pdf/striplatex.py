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
    ('plain',
     r'\begin{Verbatim}[commandchars=\\\{\}]',
     r'\begin{Verbatim}[commandchars=\\\{\},frame=single,framerule=0.3mm,rulecolor=\color{cellframecolor}]'),

    # set all Highlighting (i.e. inserted code) with a colored frame
    ('plain',
     r'\begin{Highlighting}[]',
     r'\begin{Highlighting}[frame=lines,framerule=0.6mm,rulecolor=\color{asisframecolor}]'),

    # this is about removing an extra while line at the end of the
    # 'print' area for each code cell (mind you: not the Out: area)
    ('regex',
     r'(?m)[\n\s]+\\end\{Verbatim\}',
     '\n\\\\end{Verbatim}'),
 ]

def strip_latex(in_file, out_file):

    ignoring = True
    buffer = ""

    for line in in_file:
        if r'\begin{document}' in line:
            ignoring = False
            buffer += r'%%%\begin{document}' + '\n'
            continue
        if r'\end{document}' in line:
            ignoring = True
            continue
        if r'\maketitle' in line:
            continue
        if r'Licence CC BY-NC-ND' in line:
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
    args = parser.parse_args()

    strip_latex(sys.stdin, sys.stdout)

if __name__ == '__main__':
    main()
    exit(0)
