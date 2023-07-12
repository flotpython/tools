# this would not capture files under hidden folders like .teacher
# shopt -s globstar
#focus=$(ls **/*.{py,md} | egrep -v '_build|-nb')
#ls $focus | wc -l

# ignore files that are already named in -nb
focus=$(find . -name '*.py' -o -name '*.md' | egrep -v '_build|-nb|ipynb_checkpoints')
echo "we are focusing on $(ls $focus | wc -l) files"

# debug
#echo=echo

ls $focus | sort > NAMES-ALL
nbprune -jv $focus | cut -d' ' -f1 | sort > NAMES-PLAIN

comm -3 NAMES-ALL NAMES-PLAIN > NAMES-TODO

# for testing
#echo ./python-tps/metro/README-metro.md > NAMES-TODO

TOCS="_toc.yml ../.nbhosting/nbhosting.yaml"

for filename in $(cat NAMES-TODO); do
    extension="${filename##*.}"
    stem="${filename%.*}"
    nb=${stem}-nb.${extension}
    #echo ===== $filename
    git=""
    git ls-files --error-unmatch $filename >& /dev/null && git=git
    $echo $git mv $filename $nb
    # update TOCs
    noext=$(sed -e "s|^\./||" -e "s|\.${extension}$||" <<< $filename)
    for toc in $TOCS; do
        $echo sed -i -e "s|${noext}|${noext}-nb|g" $toc
    done
done
