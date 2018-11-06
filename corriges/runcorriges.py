#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# pylint: disable=c0111

import re
from pathlib import Path
from collections import OrderedDict

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

# generate a validation notebook
import nbformat

DEBUG = False

########## helpers / filesystem

DEFAULT_COURSEDIR = "../../flotpython-course"

def check_coursedir(coursedir):
    if not (coursedir / "w1").exists():
        print(f"{coursedir} not a course dir")
        exit(1)


# where to find files like exo_carre.py, relative to COURSEDIR
SOLUTION_PATHS = ["modules/corrections", "data"]

def locate_stem(coursedir, name):
    coursedir = Path(coursedir)
    stem = Path(name).stem
    for relpath in SOLUTION_PATHS:
        for filename in [stem, f"{stem}.py"]:
            candidate = coursedir / relpath / filename
            if candidate.exists():
                return candidate
    return None


class Exomap(OrderedDict):
    """
    An object that keeps track of the association
    name -> week x sequence x source_stem
    """
    def __init__(self, coursedir):
        self.coursedir = coursedir
        self._scan()
        OrderedDict.__init__(self)

    def __repr__(self):
        return "\n".join(f"{week}-{seq}-{exo}-{source}"
                         for exo, (week, seq, source) in self.items())

    fn_pat = re.compile(r'w(?P<week>[0-9]+)-s(?P<seq>[0-9]+).*')
    ln_pat = re.compile(r'\s.*"from\s+corrections\.(?P<source>\w+).*import\s+exo_(?P<exo>\w+)')

    def _scan(self):
        for notebook in self.coursedir.glob("w?/w*-x*.ipynb"):
            match1 = self.fn_pat.match(notebook.stem)
            if not match1:
                print(f"something wrong with {notebook.stem}")
                exit(1)
            week, seq = match1.groups()
            for line in notebook.open():
                match2 = self.ln_pat.match(line)
                if match2:
                    source, exo = match2.groups()
                    self[exo] = week, seq, source
                elif 'import' in line and 'from' in line:
                    if DEBUG:
                        print(f"Warning: ignoring potential exo import\n{line}",
                              end="")


    def all_stems(self, *weeks):
        already = set()
        weeks = set(str(w) for w in weeks)
        for _, (week, _, source) in self.items():
            if week not in weeks:
                continue
            if source in already:
                continue
            already.add(source)
            yield source


class Solution:                                         # pylint: disable=r0902
    """
    an object that describes one occurrence of a function solution
    provided in the corrections/ package
    it comes with a week number, a sequence number,
    a function name, plus the code as a string

    there may be several solutions for a single function
    in general the first one is used for generating validation stuff
    """

    def __init__(self,                                  # pylint: disable=r0913
                 # mandatory
                 path, week, sequence, name,
                 # additional tags supported on the @BEG@ line
                 more=None, latex_size='small',
                 no_validation=None, no_example=None,
                 ):
        self.path = path
        self.filename = path.stem
        self.is_class = self.filename.find('cls') == 0
        self.week = week
        self.sequence = sequence
        self.name = name
        # something like 'v2' or 'suite' to label a new version or a
        # continuation
        self.more = more
        # set to footnotesize if a solution is too wide
        self.latex_size = latex_size
        # if set (to anything), no validation at all
        self.no_validation = no_validation
        # if set (to anything), no example show up in the validation nb
        self.no_example = no_example
        # internals : the Source parser will feed the code in there
        self.code = ""

    def __repr__(self):
        return f"<Solution from {self.filename} function={self.name} " \
               f"week={self.week} seq={self.sequence}>"

    def add_code_line(self, line):
        "convenience for the parser code"
        self.code += line + "\n"
# corriges.py would have the ability to do sorting, but..
# I turn it off because it is less accurate
# solutions appear in the right week/sequence order, but
# not necessarily in the order of the sequence..
#    @staticmethod
#    def key(self):
#        return 100*self.week+self.sequence


########################################
    # utiliser les {} comme un marqueur dans du latex ne semble pas
    # être l'idée du siècle -> je prends pour une fois %()s et l'opérateur %
    latex_format = r"""
\phantomsection
\addcontentsline{toc}{subsection}{
\texttt{%(name)s}%(more)s -- {\small \footnotesize{Semaine} %(week)s \footnotesize{Séquence} %(sequence)s}
%%%(name)s
}
\begin{Verbatim}[frame=single,fontsize=\%(latex_size)s, samepage=true, numbers=left,
framesep=3mm, framerule=3px,
rulecolor=\color{Gray},
%%fillcolor=\color{Plum},
label=%(name)s%(more)s - {\small \footnotesize{Semaine} %(week)s \footnotesize{Séquence} %(sequence)s}]
%(code)s\end{Verbatim}
\vspace{1cm}
"""

    def latex(self):
        name = Latex.escape(self.name)
        week = self.week
        sequence = self.sequence
        latex_size = self.latex_size
        code = self.code
        more = r" {{\small ({})}}".format(self.more) if self.more else ""
        return self.latex_format % dict(name=name, week=week, sequence=sequence,
                                        latex_size=latex_size, code=code, more=more)

    # the validation notebook
    def add_validation(self, notebook):

        class Cell:
            def __init__(self):
                self.lines = []
            def add_line(self, line):
                self.lines.append(line)
            def add_lines(self, lines):
                self.lines += lines
            def record(self):
                notebook.add_code_cell(self.lines)

        # some exercices are so twisted that we can't do anything for them here
        if self.no_validation:
            for _ in range(2):
                notebook.add_text_cell("*****")
            cell = Cell()
            cell.add_line(
                f"#################### exo {self.name} has no_validation set")
            cell.record()
            return

        notebook.add_text_cell("*****")
        # the usual case
        module = f"corrections.{self.filename}"
        exo = f"corrections.{self.filename}.exo_{self.name}"
        solution = self.name if not self.is_class else self.name.capitalize()
        cell = Cell()
        cell.add_line(f"########## exo {self.name} ##########")
        cell.add_line(f"import {module}")
        if self.no_example is None:
            cell.add_line(f"{exo}.example()")
        cell.record()
        cell = Cell()
        cell.add_line("# cheating - should be OK")
        cell.add_line(f"from {module} import {solution}")
        cell.add_line(f"{exo}.correction({solution})")
        cell.record()
        cell = Cell()
        cell.add_line(f"# dummy solution - should be KO")
        broken = f"{solution}_ko"
        cell.add_line(f"""if not hasattr({module}, '{broken}'):
    print("{broken} not found")
else:
    IPython.display.display({exo}.correction({module}.{broken}))""")

        cell.record()

########################################
    text_format = r"""
##################################################
# {name}{more} - Semaine {week} Séquence {sequence}
##################################################
{code}
"""

    def text(self):
        more = " ({})".format(self.more) if self.more else ""
        return self.text_format.format(
            name=self.name,
            more=more,
            week=self.week,
            sequence=self.sequence,
            code=self.code)

############################################################
# as of dec. 11 2014 all files are UTF-8 and that's it


class Source:                                           # pylint: disable=r0903

    def __init__(self, path, exomap):
        self.path = path
        self.exomap = exomap

    beg_matcher = re.compile(
        r"\A. @BEG@(?P<keywords>(\s+[a-z_]+=[a-z_A-Z0-9-]+)+)\s*\Z"
    )
    end_matcher = re.compile(
        r"\A. @END@"
    )
    filename_matcher = re.compile(
        r"\Aw(?P<week>[0-9]+)s(?P<sequence>[0-9]+)_"
    )

    def parse(self):                            # pylint: disable=r0912, r0914
        """
        return a tuple of
        * list of all Solution objects
        * list of unique (first) Solution per function
        that is to say, if one function has several solutions,
        only the first instance appears in tuple[1]
        """
        solution = None
        solutions = []
        functions = []
        names = []
        with self.path.open() as feed:
            for lineno, line in enumerate(feed, 1):
                # remove EOL for convenience
                if line[-1] == "\n":
                    line = line[:-1]
                begin = self.beg_matcher.match(line)
                end = self.end_matcher.match(line)
                if begin:
                    assignments = begin.group('keywords').split()
                    keywords = {}
                    for assignment in assignments:
                        key, value = assignment.split('=')
                        keywords[key] = value
                    if 'name' not in keywords:
                        print(f"{self.path}:{lineno} 'name' missing keyword")
                        continue
                    name = keywords['name']
                    if 'week' in keywords and 'sequence' in keywords:
                        print(f"{self.path}:{lineno} using explicit week and sequence")
                        self.exomap[name] = (keywords['week'],
                                             keywords['sequence'],
                                             self.path.stem)
                    else:
                        week, sequence, _ = self.exomap.get(name, (None, None, None))
                        if not week or not sequence:
                            print(f"{self.path}:{lineno} cannot spot week or sequence")
                            continue
                        keywords['week'] = week
                        keywords['sequence'] = sequence
                    try:
                        solution = Solution(path=self.path, **keywords)
                    except Exception:                   # pylint: disable=w0703
                        import traceback
                        traceback.print_exc()
                        print(f"{self.path}:{lineno}: ERROR (ignored): {line}")
                elif end:
                    if solution is None:
                        print(f"{self.path}:{lineno} - Unexpected @END@ - ignored\n{line}")
                    else:
                        # memorize current solution
                        solutions.append(solution)
                        # avoid duplicates in functions
                        if solution.name not in names:
                            names.append(solution.name)
                            functions.append(solution)
                        solution = None
                elif '@BEG@' in line or '@END@' in line:
                    print(f"{self.path}:{lineno} Warning - misplaced @BEG|END@ - ignored\n{line}")
                    continue
                elif solution:
                    solution.add_code_line(line)
        return (solutions, functions)

############################################################


class Latex:

    header = r"""\documentclass [12pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[francais]{babel}
%% for Verbatim
\usepackage{fancyvrb}
\usepackage[usenames,dvipsnames]{color}
\usepackage{hyperref}

\setlength{\oddsidemargin}{0cm}
\setlength{\textwidth}{16cm}
\setlength{\topmargin}{-1cm}
\setlength{\textheight}{22cm}
\setlength{\headsep}{1.5cm}
\setlength{\parindent}{0.5cm}
\begin{document}
\begin{center}
{\huge %(title)s}
\end{center}
\vspace{1cm}
"""

    contents = r"""
%\renewcommand{\baselinestretch}{0.75}\normalsize
\tableofcontents
%\renewcommand{\baselinestretch}{1.0}\normalsize
\newpage
"""

    footer = r"""
\end{document}
"""

    week_format = r"""
\phantomsection
\addcontentsline{{toc}}{{section}}{{Semaine {}}}
"""

    def __init__(self, path):
        self.path = path

    def write(self, solutions, title_list, contents):
        week = None
        with self.path.open('w') as output:
            title_tex = " \\\\ \\mbox{} \\\\ ".join(title_list)
            output.write(Latex.header % (dict(title=title_tex)))
            if contents:
                output.write(Latex.contents)
            for solution in solutions:
                if solution.week != week:
                    week = solution.week
                    output.write(self.week_format.format(week))
                output.write(solution.latex())
            output.write(Latex.footer)
        print(f"{self.path} (over)written")

    @staticmethod
    def escape(string):
        return string.replace("_", r"\_")

####################


class Text:                                             # pylint: disable=r0903

    def __init__(self, path):
        self.path = path

    header_format = """# -*- coding: utf-8 -*-
############################################################
#
# {title}
#
############################################################
"""

    def write(self, solutions, title_list):
        with self.path.open('w') as output:
            for title in title_list:
                output.write(self.header_format.format(title=title))
            for solution in solutions:
                output.write(solution.text())
        print(f"{self.path} (over)written")

####################


class Notebook:

    def __init__(self, path):
        self.path = path
        self.notebook = nbformat.v4.new_notebook()
        self.add_code_cell("import IPython")
        self.add_code_cell("%load_ext autoreload\n%autoreload 2")

    @staticmethod
    def _normalize(contents):
        if isinstance(contents, str):
            return contents
        if isinstance(contents, list):
            return "\n".join(contents)
        return ""

    def add_text_cell(self, contents):
        self.notebook['cells'].append(
            nbformat.v4.new_markdown_cell(
                self._normalize(contents)
            ))

    def add_code_cell(self, contents):
        self.notebook['cells'].append(
            nbformat.v4.new_code_cell(
                self._normalize(contents)
            ))

    def write(self, functions):

        for function in functions:
            function.add_validation(self)

        # JSON won't like an extra comma
        with self.path.open('w') as output:
            nbformat.write(self.notebook, output)
        print(f"{self.path} (over)written")

##########


class Stats: # pylint: disable=r0903

    def __init__(self, solutions, functions):
        self.solutions = solutions
        self.functions = functions

    def print_count(self, verbose=False):
        skipped = [f for f in self.functions if f.no_validation]
        nbsols = len(self.solutions)
        nbfuns = len(self.functions)
        nb_non_val = len(skipped)
        print(f"We have a total of {nbsols} solutions for {nbfuns} different exos "
              f" - {nb_non_val} not validated:")
        for fun in skipped:
            print(f"skipped {fun.name} - w{fun.week}s{fun.sequence}")
        if verbose:
            for fun in self.functions:
                print(fun)

####################


def main():                                      # pylint: disable=r0914, r0915
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument("-d", "--coursedir", default=DEFAULT_COURSEDIR,
                        help="The actual course directory")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument(
        "-t", "--title", default="Donnez un titre avec --title")
    parser.add_argument("-c", "--contents", action='store_true', default=False)
    parser.add_argument("-L", "--latex", action='store_true', default=False)
    parser.add_argument("-N", "--notebook", action='store_true', default=False)
    parser.add_argument("-T", "--text", action='store_true', default=False)
    parser.add_argument("weeks_or_files", nargs='+')
    args = parser.parse_args()

    # args that are numeric are considered weeks
    weeks, files = [], []
    for arg in args.weeks_or_files:
        if re.match("[0-9]+", arg):
            weeks.append(arg)
        else:
            files.append(arg)

    coursedir = Path(args.coursedir)
    check_coursedir(coursedir)

    exomap = Exomap(coursedir)
    # always store the exo map so we can detect any mishaps
    with Path("exomap.check").open('w') as output:
        output.write(str(exomap) + "\n")
    solutions, functions = [], []

    input_paths = []
    for stem in exomap.all_stems(*weeks):
        path = locate_stem(coursedir, stem)
        input_paths.append(path)
    for file in files:
        input_paths.append(Path(file))
    for path in input_paths:
        sols, funs = Source(path, exomap).parse()
        solutions += sols
        functions += funs

    if args.latex:
        do_latex = True
        do_text = False
        do_notebook = False
    elif args.text:
        do_latex = False
        do_text = True
        do_notebook = False
    elif args.notebook:
        do_latex = False
        do_text = False
        do_notebook = True
    else:
        do_latex = True
        do_text = True
        do_notebook = False

    output = args.output if args.output else "corriges"
    texoutput = Path(f"{output}.tex")
    txtoutput = Path(f"{output}.txt")
    nboutput = Path(f"{output}.ipynb")
    title_list = args.title.split(";")
    if do_latex:
        Latex(texoutput).write(
            solutions, title_list=title_list, contents=args.contents)
    if do_text:
        Text(txtoutput).write(solutions, title_list=title_list)
    if do_notebook:
        Notebook(nboutput).write(functions)
        stats = Stats(solutions, functions)
        stats.print_count(verbose=False)

if __name__ == '__main__':
    main()
