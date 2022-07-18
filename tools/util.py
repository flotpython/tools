import sys


def xpath(top, path):
    """
    navigates a nested data structure 'top' and returns the subpart corresponding to path
    path is either an iterable, or a string with steps separated with a .
    raise an exection if path s not present
    examples
    xpath({'a': 1, 'b': [{'c': 1, 'd': 1000}, {'c': 2, 'd': 2000}]},
          ['b', 0, 'd']) -> 1000
    xpath({'a': {'x': 10, 'y': {'z': 1000}}, 'b': [{'c': 1, 'd': 1000}, {'c': 2, 'd': 2000}]},
          "a.y.z")
           -> 1000
    """
    result = top
    if isinstance(path, str):
        path = path.split('.')
    for step in path:
        result = result[step]
    return result

def xpath_create(top, path, leaf_type):
    """
    like xpath but create empty entries in the structure for missing steps
    (except for int steps that are meaningful in lists only)

    leaf_type specifies the type of the empty leaf created when the path is missing

    examples
      top = {}
      xpath_create(top, 'metadata.nbhosting.title', str) -> None
      BUT afterwards top has changed to
      {'metadata': {'nbhosting': {'title': ""}}}
    """
    result = top
    if isinstance(path, str):
        path = path.split('.')
    for index, step in enumerate(path):
        if isinstance(step, int):
            result = result[step]
        else:
            if step not in result:
                result[step] = leaf_type() if (index == len(path) - 1) else {}
            result = result[step]
    return result


def truncate(s, n):
    return s if len(s) < n else s[:n - 2] + ".."

# stolen from nodemanager.tools
# replace a target file with a new contents - checks for changes
# can handle chmod if requested
# can also remove resulting file if contents are void, if requested
# performs atomically:
#    writes in a tmp file, which is then renamed(from sliverauth originally)
# returns True if a change occurred, or the file is deleted


def compare_without_trailing_newline(a ,b):
    """
    returns True if both strings are almost equal
    if any of the input strings ends with a "\n",
    it is ignored is the comparison
    """
    a_ref = a if (not a or a[-1] != "\n") else a[:-1]
    b_ref = b if (not b or b[-1] != "\n") else b[:-1]
    return a_ref == b_ref

def replace_file_with_string(target, new_contents):
    try:
        with open(target) as reader:
            current = reader.read()
    except Exception as e:
        current = ""
    if compare_without_trailing_newline(current, new_contents):
        return False
    # overwrite target file
    with open(target, 'w') as writer:
        writer.write(new_contents)
    return True
