#!/usr/bin/env python3

import sys
import re
from pathlib import Path
from enum import Enum

from util import xpath, xpath_create # replace_file_with_string, truncate

####################
import IPython

# we drop older versions, requires IPython v4
assert IPython.version_info[0] >= 4

import nbformat
from nbformat.notebooknode import NotebookNode
import jupytext

# not customizable yet
# at the notebook level

rise_metadata_padding = {
    'rise': {
        "autolaunch" : True,
        "theme": "sky",
        "start_slideshow_at": "selected",
        "slideNumber": "c/t",
        "transition": "cube",
    },
}

# this was for the video slides, it's bad on regular notebooks
rise_metadata_clear = {
#    'celltoolbar': 'Slideshow',
}

rise_metadata_force = {
    'rise': {
#        "backimage" : "media/nologo.png",
#        "width": "100%",
#        "height": "100%",
    }
}

extensions_metadata_cell_padding = {
    "deletable": True,
    "editable": True,
    "run_control": {
        "frozen": False,
        "read_only": False
    }
}

####################
# padding is a set of keys/subkeys
# that we want to make sure are defined
# this will never alter a key already present
# just add key-pair values from the default
# it means that we define these keys
# if not yet present

def pad_metadata(metadata, padding, force=False):
    """
    makes sure the keys in padding are defined in metadata
    if force is set, overwrite any previous value
    """
    for k, v in padding.items():
        if isinstance(v, dict):
            sub_meta = metadata.setdefault(k, {})
            pad_metadata(sub_meta, v, force)
        if not isinstance(v, dict):
            if force:
                metadata[k] = v
            else:
                metadata.setdefault(k, v)

def clear_metadata(metadata, padding):
    """
    makes sure the keys in padding are removed in metadata
    """
    for k, v in padding.items():
        # supertree missing in metadata : we're good
        if k not in metadata:
            continue
        if isinstance(v, dict):
            sub_meta = metadata[k]
            clear_metadata(sub_meta, v)
        if not isinstance(v, dict):
            del metadata[k]


####################
class Notebook:

    def __init__(self, name, verbose):
        if name.endswith(".ipynb"):
            name = name.replace(".ipynb", "")
        self.name = name
        #self.filename = "{}.ipynb".format(self.name)
        self.filename = self.name
        self.verbose = verbose


    def parse(self):
        try:
            with open(self.filename) as f:
                #self.notebook = nbformat.reader.read(f)
                self.notebook = jupytext.read(f)

        except:
            print(f"Could not parse {self.filename}")
            import traceback
            traceback.print_exc()


    def xpath(self, path):
        return xpath(self.notebook, path)

    def xpath_create(self, path, leaf_type):
        return xpath_create(self.notebook, path, leaf_type)

    def cells(self):
        return self.xpath('cells')

    def cell_contents(self, cell):
        return cell['source']


    def first_heading1(self):
        for cell in self.cells():
            if cell['cell_type'] == 'heading' and cell['level'] == 1:
                return xpath(cell, 'source')
            elif cell['cell_type'] == 'markdown':
                lines = self.cell_contents(cell).split("\n")
                line = lines[0]
                if line.startswith('# '):
                    return line[2:]
        return "NO HEADING 1 found"

    def set_title_from_heading1(self, force_title):
        """
        set 'nbhosting.title' in notebook metadata from the first heading 1 cell
        if force_title is provided, always set title
        if force_title is None or False, set 'nbhosting.title' only if it is not set
        """
        title = self.xpath_create('metadata.nbhosting.title', str)
        if title and force_title is None:
            pass
        else:
            if force_title == 'h1':
                new_name = self.first_heading1()
            elif force_title is not None:
                new_name = force_title
            else:
                new_name = self.first_heading1()
            self.xpath('metadata.nbhosting')['title'] = new_name
        if self.verbose:
            print(f"{self.filename} title -> {self.xpath('metadata.nbhosting.title')}")


    def fill_rise_metadata(self, rise):
        """
        if rise is set:
        if metadata is missing the 'rise' key,
        fill it with a set of hard-wired settings
        """
        if not rise:
            return
        metadata = self.notebook['metadata']
        pad_metadata(metadata, rise_metadata_padding)
        pad_metadata(metadata, rise_metadata_force, force=True)
        clear_metadata(metadata, rise_metadata_clear)

    def fill_extensions_metadata(self, exts):
        """
        if exts is set, fill each cell metadata's with a hard-wired
        set of defaults for extensions; this is to minimize git diffs
        """
        if not exts:
            return
        for cell in self.cells():
            pad_metadata(cell['metadata'], extensions_metadata_cell_padding)


    def ensure_style(self, style_rank):
        """
        make sure one of the first cells is a style cell

        the actual text is searched in a file named .style
        """

        style_path = Path(".style")

        if not style_path.exists():
            raise FileNotFoundError("the style feature requieres a .style file")

        with style_path.open() as feed:
            style_text = feed.read()

        # a bit rustic but good enough
        def is_style_cell(cell):
            source = cell['source']
            return 'HTML(' in source

        # allow the style to appear as first or second
        for cell in self.cells()[:2]:
            if is_style_cell(cell):
                cell['source'] = style_text
                break
        else:
            self.cells().insert(
                style_rank-1,
                NotebookNode({
                    "cell_type": "code",
                    "metadata": {},
                    "source": style_text,
                }))


    def ensure_license(self, license_rank):
        """
        make sure one of the first cells is a license cell

        the actual text is searched in a file named .license
        """

        license_path = Path(".license")

        if not license_path.exists():
            raise FileNotFoundError("the license feature requieres a .license file")

        with license_path.open() as feed:
            license_text = feed.read()

        # a bit rustic but good enough
        def is_license_cell(cell):
            source = cell['source'].lower()
            return 'licence' in source or 'licence' in source

        # allow the license to appear as first or second
        for cell in self.cells()[:2]:
            if is_license_cell(cell):
                cell['source'] = license_text
                break
        else:
            self.cells().insert(
                license_rank-1,
                NotebookNode({
                    "cell_type": "markdown",
                    "metadata": {},
                    "source": license_text,
                }))


    # I keep the code for these 2 but don't need this any longer
    # as I have all kinds of shortcuts and interactive tools now
    # plus, nbconvert(at least in jupyter) has preprocessor options to deal
    # with this as well
    def clear_all_outputs(self):
        """
        clear the 'outputs' field of python code cells,
        and remove 'prompt_number' as well when present
        """
        for cell in self.cells():
            if cell['cell_type'] == 'code':
                cell['outputs'] = []
                if 'prompt_number' in cell:
                    del cell['prompt_number']
                # this is now required in nbformat4
                if 'execution_count' in cell:
                    cell['execution_count'] = None


    def empty_cell(self, cell):
        try:
            return cell['cell_type'] == 'code' and not cell['input']
        except:
            return cell['cell_type'] == 'code' and not cell['source']

    def remove_empty_cells(self):
        """
        remove any empty cell - code cells only for now
        """
        nb_empty = 0
        cells_to_remove = [
            cell for cell in self.cells() if self.empty_cell(cell)]
        nb_empty += len(cells_to_remove)
        for cell_to_remove in cells_to_remove:
            self.cells().remove(cell_to_remove)
        if nb_empty:
            print(f"found and removed {nb_empty} empty cells")

    re_blank = re.compile(r"\A\s*\Z")
    re_bullet = re.compile(r"\A\s*\*\s")
    class Line(Enum):
        BLANK = 0
        BULLET = 1
        REGULAR = 2

    def line_class(self, line):
        if not line or self.re_blank.match(line):
            return self.Line.BLANK
        if self.re_bullet.match(line):
            return self.Line.BULLET
        return self.Line.REGULAR


    # this is an attempt at fixting a bad practice
    def fix_ill_formed_markdown_bullets(self):
        """
        Regular markdown has it that if a bullet list is inserted right after
        a paragraph, there must be a blank line before the bullets.
        However this somehow is not enforced by jupyter,  and being lazy
        I have ended up used this **a lot**; but that does not play well with
        pdf generation.
        """
        nb_patches = 0
        for cell in self.cells():
            if cell['cell_type'] != 'markdown':
                continue
            source = cell['source']
            # oddly enough, we observe that the logo cells
            # come up with source being a list, while all others
            # show up as str
            if type(source) is list:
                continue
            new_lines = []
            lines = source.split("\n")
            # it's convenient to take line #0 as a blank line
            curr_type = self.Line.BLANK
            for line in lines:
                next_type = self.line_class(line)
                # this seems to be the only case that matters
                if (curr_type == self.Line.REGULAR
                    and next_type == self.Line.BULLET):
                        # insert artificial newline
                        new_lines.append("")
                        nb_patches += 1
                # always preserve initial input
                new_lines.append(line)
                # remember for next line
                curr_type = next_type
            new_source = "\n".join(new_lines)
            if  new_source != source:
                cell['source'] = new_source
        if nb_patches != 0:
            print(f"In {self.name}:"
                  f"fixed {nb_patches} occurrences of ill-formed bullet")


    MAX_CODELEN = 80

    def spot_long_code_cells(self):
        """
        Prints out a warning when a code cell has a line longer than
        a hard-wired limit
        """
        for cell in self.cells():
            if cell['cell_type'] != 'code':
                continue
            source = cell['source']
            for line in source.split("\n"):
                if len(line) >= self.MAX_CODELEN:
                    print(f"{self.name} - WARNING "
                          f"code line {len(line)} longer than {self.MAX_CODELEN}")
                    print(f"{line}")


    def spot_md_escapes_4_spaces(self):
        for index, cell in enumerate(self.cells(), 1):
            if cell.cell_type != 'markdown':
                continue
            lines = cell.source if type(cell.source) is list \
                else cell.source.split("\n")
            in_backquotes = False
            for line in lines:
                if line.startswith("```"):
                    in_backquotes = not in_backquotes
                if not in_backquotes and line.startswith("    "):
                    print(f"MD4SP: {self.name}:{index} -> {line}")

    # in one ontebook of w8 we have a lot of urls
    # embedded in quoted sections of the Markdown
    # so they show up as false positive
    # could maybe be coupled with the previous spotting add-on ..
    def spot_direct_urls(self):
        for index, cell in enumerate(self.cells(), 1):
            if cell.cell_type != 'markdown':
                continue
            lines = cell.source if type(cell.source) is list \
                else cell.source.split("\n")
            for line in lines:
                match1 = re.search(r'(?P<url>http[s]?://[^/\]\)]*)/', line)
                if not match1:
                    continue
                url = match1.group('url')
                match2 = re.search(rf'\[.*\]\(.*{url}.*\)', line)
                if match2:
                    continue
                match3 = re.search(rf'<.*{url}.*>', line)
                if not match3:
                    print(f"DIRURL: {self.name}:{index} -> {line}")


    def save(self):
        jupytext.write(self.notebook, self.filename)
        print(f"{self.filename} saved")


    def full_monty(self, *, force_title, style_rank, license_rank, rise, exts, backquotes, urls):
        self.parse()
        self.clear_all_outputs()
        self.remove_empty_cells()
        self.set_title_from_heading1(force_title=force_title)
        self.fill_rise_metadata(rise)
        self.fill_extensions_metadata(exts)
        if style_rank is not None:
            self.ensure_style(style_rank)
        if license_rank is not None:
            self.ensure_license(license_rank)
        self.fix_ill_formed_markdown_bullets()
        self.spot_long_code_cells()
        if backquotes:
            self.spot_md_escapes_4_spaces()
        if urls:
            self.spot_direct_urls()
        self.save()


def full_monty(name, **kwds):
    verbose = kwds['verbose']
    del kwds['verbose']
    nb = Notebook(name, verbose)
    nb.full_monty(**kwds)


from argparse import ArgumentParser

usage = """normalize notebooks
 * Metadata
   * checks for nbhosting.title (from first heading1 if missing, or from forced name on the command line)
 * Contents
   * makes sure a correct license cell is inserted - defined in .license
   * clears all outputs
   * removes empty code cells
* Miscell
  * also notify of miscell common markdown errors
"""

def main():
    parser = ArgumentParser(usage=usage)
    parser.add_argument(
        "-t", "--force-title", action="store", dest="force_title", default=None,
        help="""force writing nbhosting.title, when provided,
                even if already present -
                provide the title, or set to 'h1' to use the first header""")
    parser.add_argument(
        "-s", "--style-rank", dest='style_rank', default=None, action='store', type=int,
        help="""make sure the style cell is up-to-date with .style;
                provide the style rank, used only for inserting a missing cell;
                default is to not manage style""")
    parser.add_argument(
        "-l", "--license-rank", dest='license_rank', default=None, action='store', type=int,
        help="""make sure the license cell is up-to-date with .license;
                provide the license cell rank, used only for inserting a missing cell;
                default is to not manage license""")
    parser.add_argument(
        "-r", "--rise", dest='rise', default=False, action='store_true',
        help="fill in RISE/livereveal metadata with hard-wired settings")
    parser.add_argument(
        "-e", "--extensions", dest='exts', action='store_true', default=False,
        help="fill cell metadata for extensions, if missing")
    parser.add_argument(
        "-b", "--backquotes", default=False, action='store_true',
        help="check for use of ``` rather than 4 preceding spaces")
    parser.add_argument(
        "-u", "--urls", default=False, action='store_true',
        help="tries to spot direct URLs, i.e. used outside of markdown []()")
    parser.add_argument(
        "-v", "--verbose", dest="verbose", action="store_true", default=False,
        help="show current nbhosting.title")
    parser.add_argument(
        "notebooks", nargs="+",
        help="the notebooks to normalize")

    args = parser.parse_args()

    for notebook in args.notebooks:
        if args.verbose:
            print(f"{sys.argv[0]} is opening notebook {notebook}")
        full_monty(
            notebook, force_title=args.force_title,
            license_rank=args.license_rank, style_rank=args.style_rank,
            rise=args.rise,
            exts=args.exts, backquotes=args.backquotes,
            urls=args.urls, verbose=args.verbose)

if __name__ == '__main__':
    main()
