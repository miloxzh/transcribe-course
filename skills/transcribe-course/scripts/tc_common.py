# -*- coding: utf-8 -*-
"""Shared helpers for the transcribe-course scripts.

Everything the individual commands have in common lives here:
workspace discovery, config loading, ffmpeg / font lookup, time formatting,
frontmatter parsing and the small text helpers used by verify/check.

A *workspace* is any folder that contains ``transcribe-course.json``.
Commands find it from ``--workspace``, the ``TC_WORKSPACE`` environment
variable, or by walking up from the current directory.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path

CONFIG_NAME = "transcribe-course.json"
SKILL_DIR = Path(__file__).resolve().parent.parent          # skills/transcribe-course/
TEMPLATE_DIR = SKILL_DIR / "templates"
PRESET_DIR = SKILL_DIR / "references" / "presets"

DEFAULTS = {
    "version": 1,
    "course": "",                    # short course name, used in tags and the log
    "language": "zh",                # Whisper language code, or "auto"
    "note_language": "zh",           # which template set to use: zh | en
    "flavor": "obsidian",            # obsidian (![[x]] + %%..%%) | markdown (![](..) + <!-- .. -->)
    "backend": "auto",               # auto | faster-whisper | mlx (Apple Silicon, needs `pip install mlx-whisper`)
    "whisper_model": "large-v3",     # faster-whisper model on GPU
    "cpu_model": "large-v3-turbo",   # faster-whisper model used automatically when no GPU is found
    "mlx_model": "mlx-community/whisper-large-v3-mlx",   # MLX model repo on Apple Silicon
    "device": "auto",                # auto | cuda | cpu (faster-whisper only)
    "ffmpeg": "",                    # optional path to ffmpeg; auto-detected when empty
    "hwaccel": "",                   # optional ffmpeg -hwaccel value, e.g. "cuda"
    "vocab_file": "vocab.txt",
    "terms_file": "terms.tsv",
    "coverage_threshold": 0.97,
    "banned_words": None,            # None -> language default (see BANNED_DEFAULT)
    "declaration_alternatives": [],  # extra first-line declarations verify accepts
    "dirs": {
        "videos": "videos",
        "transcripts": "transcripts",
        "frames": "frames",
        "notes": "notes",
        "attachments": "notes/attachments",
    },
}

# Words the note body must not contain: the note speaks in an objective voice,
# the source declaration on line one already says everything is transcribed.
BANNED_DEFAULT = {
    "zh": ["讲师"],
    "en": ["the instructor", "the lecturer", "the speaker", "the presenter"],
}

# Section headings that mean "I pasted the raw transcript" — never allowed.
RAW_DUMP_MARKERS = ["完整逐字转录", "全程逐字转录", "Raw transcript", "Full transcript (raw)", "Verbatim dump"]

TIME_COLUMNS = {"时间码", "画面时间", "来源位置", "出现时间", "时间", "画面时间码",
                "Timestamp", "Time", "Timecode", "Frame time", "Time code"}


# ---------------------------------------------------------------- console --
def setup_stdout():
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def die(msg: str, code: int = 2):
    print("✗ " + msg, flush=True)
    sys.exit(code)


def say(msg: str = ""):
    print(msg, flush=True)


# -------------------------------------------------------------- workspace --
class Workspace:
    def __init__(self, root: Path, cfg: dict):
        self.root = root
        self.cfg = cfg
        d = cfg["dirs"]
        self.videos = root / d["videos"]
        self.transcripts = root / d["transcripts"]
        self.frames = root / d["frames"]
        self.notes = root / d["notes"]
        self.attachments = root / d["attachments"]
        self.templates = root / "templates"            # optional per-workspace overrides
        self.vocab_file = root / cfg["vocab_file"]
        self.terms_file = root / cfg["terms_file"]
        self.log_file = root / "log.md"

    # config-derived conveniences
    @property
    def note_language(self) -> str:
        return self.cfg.get("note_language") or "zh"

    @property
    def flavor(self) -> str:
        return self.cfg.get("flavor") or "obsidian"

    @property
    def banned_words(self) -> list:
        b = self.cfg.get("banned_words")
        if b is None:
            return BANNED_DEFAULT.get(self.note_language, [])
        return list(b)

    def ensure_dirs(self):
        for p in (self.videos, self.transcripts, self.frames, self.notes, self.attachments):
            p.mkdir(parents=True, exist_ok=True)

    def template_dirs(self):
        """Template folders in priority order: workspace overrides, then the skill's set."""
        out = []
        if self.templates.is_dir():
            out.append(self.templates)
        lang_dir = TEMPLATE_DIR / self.note_language
        if lang_dir.is_dir():
            out.append(lang_dir)
        return out

    def templates_by_type(self) -> dict:
        """Map the `type:` value declared in each template's frontmatter to its path."""
        found = {}
        for d in self.template_dirs():
            for p in sorted(d.glob("*.md")):
                fm, _ = split_frontmatter(read_text(p))
                meta = parse_frontmatter(fm or "")
                t = meta.get("type")
                if t and t not in found:
                    found[t] = p
        return found

    def resolve_video(self, arg: str) -> Path:
        p = Path(arg).expanduser()
        if p.exists():
            return p.resolve()
        q = self.videos / arg
        if q.exists():
            return q.resolve()
        die("video not found: %s (also looked in %s)" % (arg, self.videos))

    def embed(self, filename: str) -> str:
        if self.flavor == "markdown":
            rel = os.path.relpath(self.attachments / filename, self.notes).replace(os.sep, "/")
            return "![%s](%s)" % (Path(filename).stem, rel)
        return "![[%s]]" % filename

    def stamp(self, a: float, b: float) -> str:
        rng = "%s–%s" % (fmt_mmss(a), fmt_mmss(b))
        return "<!-- %s -->" % rng if self.flavor == "markdown" else "%%" + rng + "%%"


def find_workspace(explicit: str | None = None, required: bool = True) -> Workspace | None:
    cands = []
    if explicit:
        cands.append(Path(explicit))
    if os.environ.get("TC_WORKSPACE"):
        cands.append(Path(os.environ["TC_WORKSPACE"]))
    for c in cands:
        c = c.expanduser().resolve()
        if (c / CONFIG_NAME).exists():
            return load_workspace(c)
        if required:
            die("no %s in %s" % (CONFIG_NAME, c))
    here = Path.cwd().resolve()
    for d in [here, *here.parents]:
        if (d / CONFIG_NAME).exists():
            return load_workspace(d)
    if required:
        die("not inside a transcribe-course workspace (no %s found walking up from %s). "
            "Run `tc.py init <folder>` first, or pass --workspace." % (CONFIG_NAME, here))
    return None


def load_workspace(root: Path) -> Workspace:
    cfg = json.loads(read_text(root / CONFIG_NAME) or "{}")
    merged = json.loads(json.dumps(DEFAULTS))
    for k, v in cfg.items():
        if k == "dirs" and isinstance(v, dict):
            merged["dirs"].update(v)
        else:
            merged[k] = v
    return Workspace(root, merged)


def add_workspace_arg(parser):
    parser.add_argument("--workspace", help="workspace folder (default: TC_WORKSPACE or walk up from cwd)")


# ------------------------------------------------------------------- files --
def read_text(p) -> str:
    with open(p, "r", encoding="utf-8-sig") as f:
        return f.read()


def write_text(p, text: str):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def append_log(ws: Workspace, line: str):
    from datetime import date
    prev = read_text(ws.log_file) if ws.log_file.exists() else "# transcribe-course log\n\n"
    if not prev.endswith("\n"):
        prev += "\n"
    write_text(ws.log_file, prev + "- %s %s\n" % (date.today().isoformat(), line.strip()))


def stem_of(p) -> str:
    return Path(p).stem


BAD_NAME_CHARS = re.compile(r'[\\/:*?"<>|]')


# ------------------------------------------------------------- media tools --
def find_ffmpeg(cfg: dict | None = None) -> str | None:
    """ffmpeg is optional. Order: config, FFMPEG_BINARY, PATH, imageio-ffmpeg."""
    c = (cfg or {}).get("ffmpeg") or os.environ.get("FFMPEG_BINARY")
    if c and Path(c).expanduser().exists():
        return str(Path(c).expanduser())
    w = shutil.which("ffmpeg")
    if w:
        return w
    try:
        import imageio_ffmpeg  # type: ignore
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def video_info(path) -> dict:
    """Basic stream facts via OpenCV (no ffprobe needed)."""
    import cv2
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        die("OpenCV cannot open %s" % path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    fourcc = int(cap.get(cv2.CAP_PROP_FOURCC) or 0)
    codec = "".join(chr((fourcc >> (8 * i)) & 0xFF) for i in range(4)).strip("\x00 ").lower()
    cap.release()
    return {"width": w, "height": h, "fps": fps, "frames": n,
            "duration": (n / fps) if fps else 0.0, "codec": codec}


def media_duration(path) -> float | None:
    """Duration in seconds from the container (PyAV), falling back to OpenCV."""
    try:
        import av  # type: ignore
        with av.open(str(path)) as c:
            if c.duration:
                return float(c.duration) / 1_000_000.0    # container duration is in AV_TIME_BASE units (µs)
    except Exception:
        pass
    try:
        return video_info(path)["duration"] or None
    except SystemExit:
        return None


def imread_any(path):
    """cv2.imread fails silently on non-ASCII Windows paths; decode from bytes instead."""
    import cv2
    import numpy as np
    data = np.fromfile(str(path), dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def imwrite_jpg(path, frame, quality: int = 92) -> bool:
    import cv2
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        return False
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    buf.tofile(str(path))
    return True


_FONT_CANDIDATES = [
    # Windows
    r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simhei.ttf", r"C:\Windows\Fonts\arial.ttf",
    # macOS
    "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Helvetica.ttc",
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


def find_font(size: int = 16):
    from PIL import ImageFont
    for p in _FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    try:
        return ImageFont.load_default(size)
    except TypeError:
        return ImageFont.load_default()


# -------------------------------------------------------------------- time --
def parse_time(s: str) -> float:
    """'12:34', '12:34.5', '754', '754.5' or '1:02:03' -> seconds."""
    s = str(s).strip()
    if ":" in s:
        parts = s.split(":")
        parts = [float(x) for x in parts]
        while len(parts) < 3:
            parts.insert(0, 0.0)
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    return float(s)


def fmt_mmss(sec: float) -> str:
    sec = int(sec)
    return "%02d:%02d" % (sec // 60, sec % 60)


def fmt_stamp(sec: float) -> str:
    sec = int(sec)
    return "%02d%02d" % (sec // 60, sec % 60)


# -------------------------------------------------------------------- text --
PUNCT_RE = re.compile(r"[\s，。、；：？！“”‘’（）()《》〈〉【】…—\-·,.;:?!\"'\[\]{}~～·•/\\]")
CJK_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")


def norm_text(s: str) -> str:
    return PUNCT_RE.sub("", s)


def is_cjk_text(s: str) -> bool:
    letters = [c for c in s if c.isalpha()]
    if not letters:
        return False
    return sum(1 for c in letters if CJK_RE.match(c)) / len(letters) > 0.3


def split_frontmatter(text: str):
    """Return (frontmatter_string_or_None, body)."""
    if text.startswith("---"):
        m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?", text, re.S)
        if m:
            return m.group(1), text[m.end():]
    return None, text


def parse_frontmatter(fm: str) -> dict:
    """Small YAML subset: `key: value`, `key:` followed by `- item` lines, quoted scalars."""
    meta, key = {}, None
    for raw in fm.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            continue
        m_item = re.match(r"^\s*-\s+(.*)$", line)
        if m_item and key is not None and isinstance(meta.get(key), list):
            meta[key].append(m_item.group(1).strip().strip('"').strip("'"))
            continue
        m = re.match(r"^([A-Za-z0-9_\-\u4e00-\u9fff]+):\s*(.*)$", line)
        if m and not line.startswith(" "):
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                meta[key] = []
            else:
                val = re.sub(r"\s+#.*$", "", val).strip()
                if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
                    val = val[1:-1]
                meta[key] = val
    return meta


# H3 headings that carry the hidden time range: `### Title %%mm:ss–mm:ss%%` or `<!-- mm:ss–mm:ss -->`
STAMP_RE = re.compile(
    r"^###\s+(?P<title>.*?)\s*(?:%%|<!--)\s*(?P<a>\d{1,3}):(?P<b>\d{2})\s*[–—-]\s*(?P<c>\d{1,3}):(?P<d>\d{2})\s*(?:%%|-->)\s*$")
# Older style still recognised: ### `mm:ss–mm:ss` Title
STAMP_LEGACY_RE = re.compile(r"^###\s+`(?P<a>\d{1,3}):(?P<b>\d{2})\s*[–—-]\s*(?P<c>\d{1,3}):(?P<d>\d{2})`\s*(?P<title>.*)$")
EMBED_RE = re.compile(r"!\[\[([^\]|#]+)(?:[|#][^\]]*)?\]\]|!\[[^\]]*\]\(([^)\s]+)\)")
HIDDEN_RE = re.compile(r"%%[^%]*%%|<!--.*?-->", re.S)


def h3_stamps(body: str):
    """[(title, start_sec, end_sec, line_no)] for every stamped H3 in order."""
    out = []
    for i, line in enumerate(body.split("\n"), 1):
        m = STAMP_RE.match(line) or STAMP_LEGACY_RE.match(line)
        if m:
            a = int(m.group("a")) * 60 + int(m.group("b"))
            c = int(m.group("c")) * 60 + int(m.group("d"))
            out.append((m.group("title").strip(), a, c, i))
    return out


def embeds_in(body: str):
    names = []
    for m in EMBED_RE.finditer(body):
        target = m.group(1) or m.group(2) or ""
        target = target.strip()
        if target:
            names.append(Path(target.split("?")[0]).name)
    return names


def body_without_hidden(body: str) -> str:
    return HIDDEN_RE.sub("", body)
