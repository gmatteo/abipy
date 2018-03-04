"""Database with the names of the input variables used in Abinit and in other main programs."""
from __future__ import print_function, division, unicode_literals, absolute_import

import sys
import os
import html2text

from collections import OrderedDict

# Unit names.
# Operators.
from abipy.abio.abivar_database.variables import ABI_UNITS, ABI_OPS

##############
# Public API #
##############


def get_abinit_variables():
    """Returns the database with the description of the ABINIT variables."""
    from abipy.abio.abivar_database.variables import get_codevars
    return get_codevars()["abinit"]


def docvar(varname):
    """Return the `Variable` object associated to this name."""
    return get_abinit_variables()[varname]


def abinit_help(varname, info=True, stream=sys.stdout):
    """
    Print the abinit documentation on the ABINIT input variable `varname`
    """
    database = get_abinit_variables()
    if hasattr(varname, "abivarname"): varname = varname.name
    try:
        var = database[varname]
    except KeyError:
        return stream.write("Variable %s not in database" % varname)

    html = "<h2>Default value:</h2> %s <br/><h2>Description</h2> %s" % (
        str(var.defaultval), str(var.text))
    text = html2text.html2text(html)
    if info: text += str(var.info)
    # FIXME: There are unicode chars in abinit doc (Greek symbols)
    text = text.replace("[[", "\033[1m").replace("]]", "\033[0m")

    try:
        stream.write(text)
    except UnicodeEncodeError:
        stream.write(text.encode('ascii', 'ignore'))
    stream.write("\n")


def repr_html_from_abinit_string(text):
    """
    Given a string `text` with an Abinit input file, replace all variables
    with HTML links pointing to the official documentation. Return new string.
    """
    var_database = get_abinit_variables()

    # https://stackoverflow.com/questions/6116978/python-replace-multiple-strings
    # define desired replacements here e.g. rep = {"condition1": "", "condition2": "text"}
    # ordered dict and sort by length is needed because variable names can overlap e.g. kpt, kptopt pair
    import re
    rep = {vname: var.html_link(label=vname) for vname, var in var_database.items()}
    rep = OrderedDict([(re.escape(k), rep[k]) for k in sorted(rep.keys(), key=lambda n: len(n), reverse=True)])

    # Use these three lines to do the replacement
    pattern = re.compile("|".join(rep.keys()))
    text = pattern.sub(lambda m: rep[re.escape(m.group(0))], text)
    return text.replace("\n", "<br>")
