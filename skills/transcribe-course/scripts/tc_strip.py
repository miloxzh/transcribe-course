# -*- coding: utf-8 -*-
"""Remove timestamps from a note body; keep them only in the hidden section markers.

    python tc.py strip notes/D03_周期化训练.md            # report only
    python tc.py strip --write notes/D03_周期化训练.md    # apply

Readers never need timestamps; they make the note harder to read and impossible to quote.
What this does:
  1. `### \\`mm:ss–mm:ss\\` Title`  →  `### Title %%mm:ss–mm:ss%%` (or <!-- --> in markdown flavor)
  2. inline timestamps in prose removed: `(02:04)`, `02:04–02:45`, `\\`08:12\\``, leading `03:10 text`
  3. table columns named Timestamp/时间码/画面时间/… dropped
  4. empty brackets and doubled spaces cleaned up
Placeholder section titles (e.g. "逐字转录", "Transcript") are reported, not invented: the
calling agent reads that section and writes a 4–14 character content title itself.
Frontmatter (including gaps) and attachment file names are left alone.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tc_common import TIME_COLUMNS, add_workspace_arg, find_workspace, read_text, say, split_frontmatter, write_text
from tc_verify import PLACEHOLDER_TITLES

TS = r"\d{1,2}:\d{2}"
RG = TS + r"\s*[–—-]\s*" + TS
RE_H3_OLD = re.compile(r"^###\s+`(" + RG + "|" + TS + r")`\s*(.*)$")
RE_H3_DONE = re.compile(r"^###\s+(.*?)\s*(?:%%(" + RG + "|" + TS + r")%%|<!--\s*(" + RG + "|" + TS + r")\s*-->)\s*$")
RE_TICK = re.compile(r"\s*`(?:" + RG + "|" + TS + r")`")
RE_PAREN = re.compile(r"[（(]\s*(?:" + RG + "|" + TS + r")\s*[)）]")
RE_PAREN_TXT = re.compile(r"([（(])(?:" + RG + "|" + TS + r")\s+")
RE_LEAD = re.compile(r"^(\s*(?:[-*]\s+|\d+\.\s+)?)(?:" + RG + "|" + TS + r")\s+")
RE_BARE_RG = re.compile(r"(?<![\d.])" + RG + r"(?![\d.])")
RE_LEFT_TS = re.compile(r"(?<![\d.:])" + TS + r"(?![\d.:])")


def drop_table_cols(lines):
    out, i, n, dropped = [], 0, len(lines), 0
    while i < n:
        l = lines[i]
        if l.lstrip().startswith("|") and i + 1 < n and re.match(r"^\s*\|?\s*:?-{2,}", lines[i + 1]):
            header = [c.strip() for c in l.strip().strip("|").split("|")]
            idx = [k for k, c in enumerate(header) if c in TIME_COLUMNS]
            j = i
            while j < n and lines[j].lstrip().startswith("|"):
                cells = lines[j].strip().strip("|").split("|")
                if idx and len(cells) >= len(header):
                    cells = [c for k, c in enumerate(cells) if k not in idx]
                    out.append("|" + "|".join(cells) + "|")
                else:
                    out.append(lines[j])
                j += 1
            if idx:
                dropped += 1
            i = j
        else:
            out.append(l)
            i += 1
    return out, dropped


def process(text: str, flavor: str, stats: dict) -> str:
    fm, body = split_frontmatter(text)
    head = ("---\n" + fm + "\n---\n") if fm is not None else ""
    lines = body.split("\n")
    lines, stats["table_cols"] = drop_table_cols(lines)
    out = []
    for l in lines:
        m = RE_H3_OLD.match(l)
        if m:
            rng, title = m.group(1).replace(" ", ""), m.group(2).strip()
            if not title or PLACEHOLDER_TITLES.match(title):
                stats["placeholders"].append(rng)
                title = title or "逐字转录"
            marker = ("<!-- %s -->" % rng) if flavor == "markdown" else "%%" + rng + "%%"
            out.append("### %s %s" % (title, marker))
            stats["h3"] += 1
            continue
        md = RE_H3_DONE.match(l)
        if md:
            if not md.group(1).strip() or PLACEHOLDER_TITLES.match(md.group(1).strip()):
                stats["placeholders"].append(md.group(2) or md.group(3))
            out.append(l)
            continue
        before = l
        l = RE_LEAD.sub(r"\1", l)
        l = RE_PAREN.sub("", l)
        l = RE_PAREN_TXT.sub(r"\1", l)
        l = RE_TICK.sub("", l)
        l = RE_BARE_RG.sub("", l)
        if l != before:
            stats["inline"] += 1
        l = re.sub(r"[（(]\s*[)）]", "", l)
        l = re.sub(r"[ \t]{2,}", " ", l)
        l = re.sub(r"\s+([。，；：！？）])", r"\1", l)
        l = re.sub(r"[ \t]+$", "", l)
        out.append(l)
    body = "\n".join(out)
    hidden_removed = re.sub(r"%%[^%]*%%|<!--.*?-->", "", body, flags=re.S)
    hidden_removed = re.sub(r"!\[[^\]]*\]\([^)]*\)|!\[\[[^\]]*\]\]", "", hidden_removed)
    stats["leftover"] = RE_LEFT_TS.findall(hidden_removed)[:5]
    return head + body


def main(argv):
    ap = argparse.ArgumentParser(prog="tc strip", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes", nargs="+")
    ap.add_argument("--write", action="store_true", help="write changes (default: report only)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    rc = 0
    for n in a.notes:
        p = Path(n)
        text = read_text(p)
        stats = {"h3": 0, "inline": 0, "table_cols": 0, "placeholders": [], "leftover": []}
        new = process(text, ws.flavor, stats)
        flag = ""
        if stats["placeholders"]:
            flag += "  ⚠ placeholder titles at %s (write content titles)" % " ".join(stats["placeholders"])
            rc = 1
        if stats["leftover"]:
            flag += "  ⚠ leftover: %s" % " ".join(stats["leftover"])
        say("%-40s H3 %2d | inline %3d | table cols %d%s" % (p.name[:40], stats["h3"], stats["inline"], stats["table_cols"], flag))
        if a.write and new != text:
            write_text(p, new)
            say("  written")
    if not a.write:
        say("(report only — add --write to apply)")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
