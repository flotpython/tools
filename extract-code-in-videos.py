#!/usr/bin/env python
"""
tool to produce files like e.g.
w1/w1-s3-av-code.html

sources are in the form
w1/w1-code-in-videos.md

this tool will update as many files of the form

w1/w1-s3-av-code.html

as are mentioned in the sources

Run as follows:

$ cd flotpython-course
$ python ../flotpython-tools/extract-code-in-videos.py w?/w*-code-in-videos.md

"""

import re
from argparse import ArgumentParser
from pathlib import Path
from myst_parser.main import to_html

sequence_pattern = r"# w(?P<week>[0-9])s(?P<seq>[0-9])"
sequence_matcher = re.compile(sequence_pattern)

header = """
<style>
.clipboard {
    font-size: 11px;
}
</style>
<h3 style="border: 1px solid #66b; border-radius: 5px; padding: 10px; background-color: #eee;">
<b><i>bloc-note pour copier/coller le code de la vidéo</i></b>
</h3>

"""

def save_sequence(week, seq, lines):
    filename = f"w{week}/w{week}-s{seq}-av-code.html"
    print(f"using {len(lines)} (markdown) lines to make {filename}")
    text ="".join(lines)
    with Path(filename).open('w') as writer:
        writer.write(f"<div class='clipboard'>{to_html(text)}</div>")

def handle_week(markdown):
    with open(markdown) as feed:
        lines = []
        week, seq = None, None
        for line in feed:
            if match := sequence_matcher.match(line):
                # flush previous sequence if needed
                if lines:
                    if week:
                        save_sequence(week, seq, lines)
                    # potential leak ?
                    else:
                        # allow empty lines
                        meaningful = [line.strip() for line in lines]
                        meaningful = [line for line in meaningful if line]
                        if meaningful:
                            print("OOPS !")
                week, seq = match.groups()
                #print(f"spotted week={week} seq={seq} with {len(lines)} lines")
                lines = []
                lines.append(header)
                # lines.append(line)
            else:
                lines.append(line)
        save_sequence(week, seq, lines)
        #print(f"EOF with week={week} seq={seq} and {len(lines)} lines")


def main():
    parser = ArgumentParser()
    parser.add_argument("markdowns", nargs='+')
    args = parser.parse_args()
    
    for markdown in args.markdowns:
        handle_week(markdown)

if __name__ == '__main__':
    main()
