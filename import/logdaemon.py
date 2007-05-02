# -*- eval: (setq py-python-command "sudo -u anand python") -*-

import sys
sys.path.insert(0, "../infogami")

logfile = '/1/dbg/import-logs/dbglog'
logfile = '/tmp/dbglog'

from infogami.tdb.logger import parse, parse2a, parse2
import web

import re
from itertools import *
from itools import *
from operator import itemgetter
fst = itemgetter(0)
snd = itemgetter(1)

def setup():
    web.config.db_parameters = dict(dbn="postgres",
                                    db="dbglog",
                                    user="pharos",
                                    pw="pharos")
    web.load()

# @slicer(5)
def logparse(logfile):
    return parse2a(parse(logfile))

def speed():
    from time import time
    p = logparse(logfile)
    t0=time()
    print sum(1 for x in p)
    print time()-t0

setup()

# ================================================================

from exclude import excluded_fields

def emit(out, field_name, field_val, non_strings = set()):
    from cgi import escape
    assert escape(field_name) == field_name

    if type(field_val) == list:
        for v in field_val:
            emit(out, field_name, v)
    else:
        # some fields are numeric--may need to pad these with
        # leading zeros for sorting purposes, but don't bother for now. @@
        if type(field_val) != str:
            field_val = str(field_val)
            if field_name not in non_strings:
                # temporarily print out names of fields which
                # are found to (sometimes) actually contain a
                # non-string value.
                print 'non-string fieldname', field_name
                non_strings.add(field_name)

        print >>out, "  <field name=%s>%s</field>"% (field_name,
                                              escape(field_val))
    
def main():
    global t,k
    out = open('solr.xml', 'w')

    for i,t in enumerate(logparse(logfile)):
        # print list(k for k in t.d)
        if i % 100 == 0:
            print i,
            sys.stdout.flush()
        print >>out, "<add><document>"
        for k in t.d:
            assert k != 'text'
            v = getattr(t.d, k)
            emit(out, k, v)
            if k not in excluded_fields:
                emit(out, 'text', v)
        print >>out, "</document></add>\n"

main()