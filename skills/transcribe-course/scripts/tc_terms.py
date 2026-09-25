# -*- coding: utf-8 -*-
"""Apply the workspace terms.tsv (known mis-hearings → correct terms) to a note.

    python tc.py terms notes/D03_周期化训练.md            # report
    python tc.py terms --write notes/D03_周期化训练.md    # apply and record in frontmatter term_fixes

terms.tsv holds one pair per line, tab-separated: `wrong<TAB>right`. Only add pairs that cannot
mean anything else in this course — the replacement is blind. Every replacement is merged into the
frontmatter line `term_fixes: "wrong→right×n, …"` so the correction trail stays with the note; the
writing agent's own entries in that line are kept and counts are added, never overwritten.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import OrderedDict
from pathlib import Path

from tc_common import add_workspace_arg, find_workspace, read_text, say, split_frontmatter, write_text


def load_terms(path: Path):
    pairs = []
    if not path.exists():
        return pairs
    for line in read_text(path).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            parts = re.split(r"\s*(?:→|->)\s*", line.strip(), maxsplit=1)
        if len(parts) >= 2 and parts[0].strip() and parts[1].strip():
            pairs.append((parts[0].strip(), parts[1].strip()))
    return pairs


def merge_term_fixes(fm: str, done: list) -> str:
    merged = OrderedDict()
    m_old = re.search(r'term_fixes:\s*"(.*)"', fm)
    old_items = re.split(r"[，,]\s*", m_old.group(1)) if m_old else []
    for item in old_items + done:
        item = item.strip()
        if not item:
            continue
        if "×" in item:
            k, n = item.rsplit("×", 1)
            n_int = int(re.match(r"\d+", n).group(0)) if re.match(r"\d+", n) else 1
            merged[k] = merged.get(k, 0) + n_int
        else:
            merged[item] = merged.get(item, 0)
    line = 'term_fixes: "' + "，".join(("%s×%d" % (k, v)) if v else k for k, v in merged.items()).replace('"', "'") + '"'
    if "term_fixes:" in fm:
        return re.sub(r"term_fixes:.*", lambda _m: line, fm)
    return fm.rstrip("\n") + "\n" + line


def main(argv):
    ap = argparse.ArgumentParser(prog="tc terms", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes", nargs="+")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--terms", help="alternative terms file (default: workspace terms.tsv)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    pairs = load_terms(Path(a.terms) if a.terms else ws.terms_file)
    if not pairs:
        say("no term pairs in %s — nothing to do" % (a.terms or ws.terms_file))
        return 0
    total = 0
    for n in a.notes:
        p = Path(n)
        text = read_text(p)
        fm, body = split_frontmatter(text)
        done = []
        for bad, good in pairs:
            c = body.count(bad)
            if c:
                body = body.replace(bad, good)
                done.append("%s→%s×%d" % (bad, good, c))
        if not done:
            say("%-40s no matches" % p.name[:40])
            continue
        total += sum(int(d.rsplit("×", 1)[1]) for d in done)
        say("%-40s %s" % (p.name[:40], "，".join(done)))
        if a.write:
            new = ("---\n" + merge_term_fixes(fm, done) + "\n---\n" + body) if fm is not None else body
            write_text(p, new)
            say("  written")
    say("total replacements %d | %s" % (total, "written" if a.write else "report only (--write to apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
