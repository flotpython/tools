#!/usr/bin/env python3

from pathlib import Path
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter


# comme on ne peut plus ranger les titres de chapitre dans Python.tex
# on les met dans un fichier à part

def read_title(target_week):
    with open("ChapterNames.txt") as feed:
        for line in feed:
            week, title = line.split(':')
            iweek = week.strip()
            if iweek == target_week:
                return title.strip()
    return f"Titre pas trouvé pour semaine {target_week}"


# on retrouve les noms des notebooks appartenant à une semaine
# grâce à un simple pattern matching sur les w<i>-s*.tex
def notebook_names(target_week, workdir):
    workpath = Path(workdir)
    pattern = f"w{target_week}-s*.tex"
    for nbpath in workpath.glob(pattern):
        yield nbpath.stem


# créer le fichier .tex qui contient ce qu'on veut montrer
def write_output(weekrange, first_chapter, outputname, workdir):
    with open(outputname, "w") as output:
        for index, week in enumerate(weekrange):
            title = read_title(week)

            # index == 0 correspond au premier chapitre dans le .tex
            if index == 0:
                # ajouter le numéro du chapitre = numéro de semaine
                output.write(rf"\setcounter{{chapter}}{{{int(first_chapter)-1}}}" "\n")
            output.write("\n" rf"\chapter{{{title}}}" "\n")
            if index == 0:
                output.write(r"\pagestyle{moocpagestyle}" "\n")
                output.write(r"\setcounter{page}{1}" "\n")

            # les notebooks du chapitre
            for notebook in notebook_names(week, workdir):
                output.write(rf"\input{{{notebook}}}" "\n")


# ya plus qu'à
def main():
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-f', '--from', dest='w_from', type=int, default=1,
                        help='first week')
    parser.add_argument('-t', '--to', dest='w_to', type=int, default=9,
                        help='last week')
    parser.add_argument('-o', '--output', default="work/contents.tex",
                        help='output tex')
    parser.add_argument('-w', '--work-dir',
                        dest='workdir', default="work")
    parser.add_argument("weeks", nargs='*')

    args = parser.parse_args()

    # can either give a list of weeks, or specify a range
    # but not both
    if args.weeks:
        weekrange = args.weeks
        first_chapter = args.weeks[0]
    else:
        weekrange = [str(w) for w in range(args.w_from, args.w_to+1)]
        first_chapter = args.w_from

    write_output(weekrange, first_chapter, args.output, args.workdir)


if __name__ == '__main__':
    main()
