# -*- coding: utf-8 -*-
"""Append one dated line to the workspace log.md.

    python tc.py log "D03 transcribed 102 s, 11 slides, 9 attached, coverage 100%"
"""
import argparse

from tc_common import add_workspace_arg, append_log, find_workspace, say


def main(argv):
    ap = argparse.ArgumentParser(prog="tc log", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("text", nargs="+", help="the line to append (quotes optional)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    append_log(ws, " ".join(a.text))
    say("→ %s" % ws.log_file)
    return 0
