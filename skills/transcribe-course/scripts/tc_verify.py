# -*- coding: utf-8 -*-
"""Mechanical checks on a note — the part of the spec a script can enforce.

    python tc.py verify notes/D03_周期化训练.md
    python tc.py verify notes/*.md

The note's `type:` selects a template (workspace templates/ first, then the skill's
templates/<note_language>/). The template is the contract:
  - the `## ` headings must match it exactly, in order (downstream tools search by heading);
  - the first line after the H1 must be the template's source declaration;
  - a `<!-- tc:chronological min=N -->` marker under a heading means that section must hold
    at least N stamped `### Title %%mm:ss–mm:ss%%` sub-sections in increasing time order.
Also checked: required frontmatter, `verified: pass`, banned words (objective voice), no
timestamps in the body, no raw-transcript dumps, no U+FFFD, every embedded image exists.

Exit code 0 = all PASS, 1 = at least one FAIL. WARN lines never fail the note.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from tc_common import (RAW_DUMP_MARKERS, TIME_COLUMNS, add_workspace_arg, body_without_hidden, embeds_in,
                       find_workspace, h3_stamps, parse_frontmatter, read_text, say, split_frontmatter)

REQUIRED_KEYS = ["type", "source_file", "video_length", "whisper_model", "processed", "verified"]
PLACEHOLDER_TITLES = re.compile(r"^(逐字转录|转录|第?\s*\d+\s*段|段落\s*\d+|transcript|segment\s*\d*|part\s*\d+|section\s*\d+)$", re.I)
SPEC_RESTATED = ["本规范", "作业规范", "per the spec", "this specification", "the transcription spec"]
LEFTOVER_TS = re.compile(r"(?<![\d.:])\d{1,2}:\d{2}(?![\d.:])")


def _q(s: str) -> str:
    return s.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'").strip()


def template_contract(tpl_path: Path) -> dict:
    """What the template demands: H2 list, declaration line, chronological markers."""
    fm, body = split_frontmatter(read_text(tpl_path))
    lines = body.split("\n")
    h2, decl, chrono = [], None, {}
    current = None
    seen_h1 = False
    for line in lines:
        if line.startswith("# ") and not seen_h1:
            seen_h1 = True
            continue
        if line.startswith("## "):
            current = _q(line[3:])
            h2.append(current)
            continue
        if decl is None and seen_h1 and not h2 and line.startswith("> "):
            decl = line.strip()
        m = re.search(r"<!--\s*tc:chronological(?:\s+min=(\d+))?\s*-->", line)
        if m and current:
            chrono[current] = int(m.group(1) or 1)
    return {"h2": h2, "declaration": decl, "chronological": chrono, "meta": parse_frontmatter(fm or "")}


def run(path: Path, ws):
    fails, warns = [], []
    raw = read_text(path)
    fm, body = split_frontmatter(raw)
    if fm is None:
        return ["no frontmatter"], [], {}
    meta = parse_frontmatter(fm)
    templates = ws.templates_by_type()
    typ = meta.get("type", "")
    if typ not in templates:
        fails.append("type %r has no template; known types: %s" % (typ, ", ".join(templates) or "none"))
        return fails, warns, {"chars": 0}
    contract = template_contract(templates[typ])

    for k in REQUIRED_KEYS:
        if k not in meta or meta[k] in ("", []):
            fails.append("frontmatter missing %s" % k)
    if meta.get("verified") != "pass":
        fails.append("frontmatter verified is not 'pass' (second-pass check not done)")
    vl = str(meta.get("video_length", ""))
    if not re.match(r"^\d{1,2}:\d{2}(:\d{2})?$", vl):
        fails.append("video_length %r is not m:ss / mm:ss / h:mm:ss" % vl)

    text = body.strip()
    lines = text.split("\n")
    visible = body_without_hidden(text)

    # declaration: first non-empty line after the H1
    first = ""
    seen_h1 = False
    for l in lines:
        if l.startswith("# ") and not seen_h1:
            seen_h1 = True
            continue
        if seen_h1 and l.strip():
            first = l.strip()
            break
    accepted = [contract["declaration"]] + list(ws.cfg.get("declaration_alternatives") or [])
    if contract["declaration"] and _q(first) not in [_q(x) for x in accepted if x]:
        fails.append("first line after the title is not the source declaration: %r" % first[:60])

    # H2 contract
    h2 = [_q(l[3:]) for l in lines if l.startswith("## ")]
    want = contract["h2"]
    if h2 != want:
        fails.append("H2 headings differ from template %s:\n      have  %s\n      want  %s" % (
            templates[typ].name, " | ".join(h2), " | ".join(want)))

    # chronological sections
    stamps = h3_stamps(text)
    prev = -1
    for title, s, e, ln in stamps:
        if s < prev:
            fails.append("time order goes backwards at line %d (%s) — reorganised by topic?" % (ln, title))
        if e - s > 185:
            warns.append("section '%s' spans %d s (> 3 min)" % (title, e - s))
        if e < s:
            fails.append("section '%s' ends before it starts" % title)
        if PLACEHOLDER_TITLES.match(title or ""):
            fails.append("placeholder section title at line %d: %r — write a content title" % (ln, title))
        prev = s
    for heading, n_min in contract["chronological"].items():
        # count stamped H3s under that H2
        sec_text = _section(text, heading)
        n = len(h3_stamps(sec_text))
        if n < n_min:
            fails.append("'%s' has %d stamped sub-sections, template asks for at least %d" % (heading, n, n_min))

    # voice, dumps, encoding, timestamps
    for w in ws.banned_words:
        c = visible.count(w)
        if c:
            fails.append("body contains banned word %r ×%d (write objective statements)" % (w, c))
    for m in RAW_DUMP_MARKERS:
        if m in text:
            fails.append("raw transcript dump marker %r present ×%d" % (m, text.count(m)))
    if "\ufffd" in text:
        fails.append("contains U+FFFD replacement character ×%d" % text.count("\ufffd"))
    for s in SPEC_RESTATED:
        if s in visible:
            fails.append("body restates the spec (%r)" % s)
    scrub = re.sub(r"!\[[^\]]*\]\([^)]*\)|!\[\[[^\]]*\]\]", "", visible)     # embeds carry mmss in names
    left = LEFTOVER_TS.findall(scrub)
    if left:
        fails.append("timestamps left in the body ×%d (e.g. %s)" % (len(left), " ".join(left[:3])))
    for l in lines:
        if l.lstrip().startswith("|"):
            cells = [c.strip() for c in l.strip().strip("|").split("|")]
            hit = [c for c in cells if c in TIME_COLUMNS]
            if hit:
                fails.append("table has a time column %r — run `tc.py strip --write`" % hit[0])
                break

    # embeds
    embeds = embeds_in(text)
    for e in embeds:
        cand = [ws.attachments / e, path.parent / e, path.parent / "attachments" / e]
        if not any(c.exists() for c in cand):
            fails.append("embedded image not found in %s: %s" % (ws.attachments, e))
    declared = str(meta.get("images", ""))
    if declared.isdigit() and int(declared) != len(embeds):
        warns.append("images: %s declared but %d embedded" % (declared, len(embeds)))

    chars = len(re.sub(r"\s", "", visible))
    return fails, warns, {"chars": chars, "sections": len(stamps), "images": len(embeds), "type": typ}


def _section(text: str, heading: str) -> str:
    parts = re.split(r"(?m)^(?=## )", text)
    for p in parts:
        if p.startswith("## ") and _q(p.split("\n", 1)[0][3:]) == _q(heading):
            return p
    return ""


def main(argv):
    ap = argparse.ArgumentParser(prog="tc verify", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("notes", nargs="+", help="note file(s)")
    add_workspace_arg(ap)
    a = ap.parse_args(argv)
    ws = find_workspace(a.workspace)
    rc = 0
    for n in a.notes:
        p = Path(n)
        if not p.exists():
            say("✗ not found: %s" % n)
            rc = 1
            continue
        fails, warns, info = run(p, ws)
        say("%s | type %s | chars %s | sections %s | images %s" % (
            p.name, info.get("type", "?"), info.get("chars", "?"), info.get("sections", "?"), info.get("images", "?")))
        for f in fails:
            say("  FAIL " + f)
        for w in warns:
            say("  WARN " + w)
        if not fails:
            say("  PASS")
        else:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
