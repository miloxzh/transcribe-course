# Transcription spec — course video → verbatim-level note (v3)

This is the rulebook for the **writing agent**. It turns one video's Whisper transcript plus a
handful of selected frames into one Markdown note. The note exists so that **the reader never has
to watch the video again**: it must contain everything in the video, not your understanding of it.

Version history: v2 (2026-09) was written for one fitness course and one Obsidian vault; v3 keeps
every content rule and removes the course-specific paths, names and folder rules. Templates and
markers now come in a Chinese and an English set; the brief tells you which.

---

## 0. Twelve rules before you start

1. **You are a transcriber, not an analyst.** No summarising, no regrouping, no evaluating, no
   supplementing, no correcting what was taught.
2. **Speaking order, never topic order.** Whatever order the course presents things in, the note follows.
3. **Everything is recorded** — the single exception is repetition as defined in §2.
4. **No number is dropped, and every number carries its unit or context.**
5. **Slides are copied into the prose word for word, then the image is embedded** (§5).
6. **The course's own closing summary is kept verbatim in its own section.**
7. **Any plan, protocol or prescription is kept in full**: exercise, sets, reps, rest, RPE, cues —
   from the screen and from speech.
8. **No timestamps in the prose.** A section title is a content title; its time range is hidden
   in a comment at the end of the heading (§7).
9. **Inaudible → mark it. Doubtful term → check the screen first, then mark it. Never guess** (§4).
10. **A correction you can prove goes in silently and is logged in `term_fixes`; one you cannot
    prove keeps the original word plus a doubt marker** (§4).
11. **Second pass before delivery** (§6). Without it there is no `verified: pass`.
12. **Write only the one output file named in the brief.** Read what the brief lists; touch nothing else.

---

## 1. Three red lines

### 1.1 Do not change the content
If the course says something wrong, record it wrong. The moment you "fix it in passing", the reader
can no longer know what the course actually taught.
- No knowledge from outside the video.
- No merging of similar phrasings — the difference in wording is information.
- No collapsing a range into one value ("10–20 sets" never becomes "about 15 sets").
- **When the course contradicts itself, record both places** and add one line to `gaps` in the frontmatter.

### 1.2 Do not compress
A note written as a thematic overview ("applications", "summary of the lesson") at half the length
of a verbatim note is analysis, not transcription.

- ❌ `The course recommends 1–5RM work to raise recruitment and firing rate, placed early in the session.` ← your summary
- ✅ **Every sentence actually said**: how the topic was introduced, the example, the analogy, the
  number, the qualifier, how it was wrapped up.

**The measure is coverage, not word count.** Every transcript segment must be findable in the note
(the gate looks for 4-character or 3-word shingles and wants ≥ 97 %). Do not pad to reach a
length. **Do not paste the raw transcript anywhere to reach coverage** — no "Full transcript"
block after a section, no section made of uncorrected Whisper lines. Coverage must come from
corrected prose placed in the right section; if something is missing, put that sentence where it
belongs.

**Distinguish "you were brief" from "the course was brief".** If the speaker only named a term
without explaining it, write "only the term X is mentioned here, not explained". That is
information, not an excuse to compress.

### 1.3 Do not guess

| Situation | Chinese notes | English notes |
|---|---|---|
| Cannot hear it | `[听不清]` | `[inaudible]` |
| Cannot read the screen | `[画面不清]` | `[screen unclear]` |
| Term looks mis-transcribed, no proof | keep the word, add `[转写存疑，疑为"X"]` | keep the word, add `[unclear, possibly "X"]` |
| You are inferring, not hearing | `[推断]` + the basis | `[inferred]` + the basis |

Markers go inline where the problem is. Only "a stretch was skipped" and "the course contradicts
itself" go into `gaps`.

---

## 2. The only allowed omission: repetition

**Repetition = the same point said again with nothing new.**
- First occurrence: record in full.
- Later occurrence: one line in that place — zh `（再次强调「XX」，无新增内容）`, en `(repeats "XX", nothing new)`.
- **If the repetition adds anything — a number, an example, a qualifier, a counter-example — record it in full. It is not repetition.**

Two more things may be reduced to one line, but the line must exist:
- Greetings, closing promotion, unrelated chat: zh `（开场寒暅，无课程内容）` / en `(Greeting, no course content.)`
- A slip of the tongue the speaker corrects: record only the corrected version, mark zh `（口误已更正）` / en `(self-corrected slip)`.

Nothing else may be left out.

---

## 3. Your inputs

The brief lists exact paths. Typically:

| Input | What it is for |
|---|---|
| `transcripts/{stem}.txt` | The primary source: `mm:ss  text`, one Whisper segment per line. Read it top to bottom. |
| `transcripts/{stem}.json` | The same segments with start/end seconds. Used for the second pass (§6). |
| `frames/{stem}/framelist.md` | Which frames go into the note (with what is on them) and which frames only serve as evidence (burned-in subtitle text, screen text). |
| `notes/attachments/` | The frames already chosen for the note, named `{prefix}_{mmss}_{label}.jpg`. Embed by file name only. |
| `frames/{stem}/*.jpg`, `_sheet_*.jpg` | All candidate frames, if you need to look closer. |
| The brief's correction table | Mis-hearings the operator already confirmed from the screen or subtitles. |

Whisper output is good but not perfect: homophones in domain terms are the typical error, and a
few `�` characters can appear. Burned-in subtitles (the text at the bottom of the frame) were
proofread by the video editor and are the most reliable spelling source; slide text is equally hard
evidence.

---

## 4. Correcting the transcript

Change a word only when one of these proves it:
1. it is printed on a slide or in a burned-in subtitle in a frame you looked at;
2. the brief's correction table lists it;
3. it is an unambiguous domain term the transcript mangled into a homophone (肌结→肌节, "sarcomer"→"sarcomere"),
   and the corrected word fits the sentence.

How to mark it:
- **Proven correction: write the corrected word in the prose with no bracket, no footnote.** Log
  every distinct change once in the frontmatter line `term_fixes: "wrong→right×count, …"`
  (comma-separated; put it before `gaps:`). Readers get clean prose; the audit trail stays in the frontmatter.
- **Not proven: keep the original word and add the doubt marker from §1.3.** Do not replace it with a
  guess, however plausible — a guess made from context has been wrong before while the subtitle
  showed a third word.
- **`�` characters:** fill in from context, log as `转写乱码→X` / `garbled→X` in `term_fixes`, and never
  let `�` reach the note (the gate fails on it).
- **Do not over-correct.** A change that reads well but does not match the surrounding sentences is a
  new error. If the "correct" term makes the sentence say something different, revert and mark doubt.

---

## 5. Frames: copy the text, then embed the image

The operator already chose the frames and wrote `framelist.md`. For each frame listed as "goes into the note":
1. Open it with Read and read it yourself — the list is an index, not a transcription.
2. In the section covering that time range, **write out every word, number, table row, axis label and
   annotation on the frame**, in prose or as a Markdown table. Include what the speaker did not read aloud —
   the numbers on slides are often the main content of the lesson.
3. Then embed the image on its own line: Obsidian flavor `![[D06_0404_four-effects.jpg]]`, Markdown flavor
   `![four effects](attachments/D06_0404_four-effects.jpg)` — the brief says which.

**The image is a supplement; the text is the record.** Search works on text; images can be lost.
An image without its text copied out counts as not recorded.

Frames listed as "evidence only" (subtitle strips, demo shots) are for spelling and for checking
plan details; they are not embedded unless the framelist says so.

---

## 6. Second pass — the delivery gate

After the first draft, go through `transcripts/{stem}.json` from the first segment to the last and
check each one against the note:
1. The segment's content is present in the note → fine.
2. It is not → either add it to the right section, or it is repetition/greeting under §2 and the
   one-line marker is already there.
3. Every frame in the framelist's "goes into the note" table is embedded, and its text is in the prose.
4. Sections appear in time order (check the hidden ranges on the H3s).

Only then write `verified: pass` in the frontmatter. A note without that line is unfinished.

---

## 7. Timestamps and section titles

Timestamps mean nothing to a reader. Rules:
1. **No timestamp anywhere in the prose**: not `(02:04–02:45)` after a sentence, not `` `08:12` `` as a
   reference, no "time" column in tables, no times on quotes.
2. **Every sub-section has a content title**: `### Title %%mm:ss–mm:ss%%` (Obsidian) or
   `### Title <!-- mm:ss–mm:ss -->` (Markdown). Title: 4–14 characters (CJK) / 3–10 words (English), a
   noun phrase or short sentence saying what the stretch is about — "The four zones of a sarcomere",
   "Why eccentric work causes the most damage", "Exercise 3 of the men's plan: dumbbell stiff-leg deadlift".
   **Placeholders such as "Transcript", "Part 1", "逐字转录" are forbidden.** No two titles the same in one note.
3. The time range lives only in that hidden comment; the second pass and the checking scripts use it.
4. Technique notes carry no times in their bullet points either; "said three times" is enough.
5. The `mmss` in an attachment file name is allowed — it is a file name, not prose.
6. **Never paste transcript lines by time range into any section**, and never append a "full transcript"
   block after a section. One body per section, made of corrected complete sentences.
7. Files are written UTF-8. A single `�` fails the gate.

---

## 8. Voice

Readers use the note as knowledge and share it. Do not write "the instructor says / thinks". The
fidelity is guaranteed by the declaration on the first line of the body (it is in the template).

Three things must survive:
1. The speaker's own qualifiers ("may", "not necessarily", "controversial", "personally I") — removing
   them changes the certainty of the claim.
2. A statement the speaker flags as personal opinion → zh `课程主张……` / en `The course holds that …`.
3. Slide and speech disagree → record both and say which is which.

---

## 9. Output

- **One file**, the path given in the brief. Nothing else is written or modified.
- **Use the template the brief names** (`templates/<language>/lecture.md` or `technique.md`, or a
  workspace override). **Second-level headings (`## `) are copied character for character, emoji included,
  in the template's order, and every one of them is present** — write "None." / "无。" under a heading that
  has no content rather than deleting it. Downstream tools search by heading.
- The template's blockquote lines under headings are instructions to you, not text to copy. The only
  blockquote that goes into the note is the source declaration under the H1.
- Frontmatter: fill every key the template shows. `video_length` as `mm:ss`; `whisper_model` and
  `source_file` as given in the brief; `images` = number of embeds; `verified: pass` only after §6;
  `term_fixes` and `gaps` as described above. For technique notes, `aliases` lists every name used
  for *this* movement (spoken, printed, on the machine, short forms) and never an alternative movement.
- Length: whatever covers the transcript. Do not pad; do not trim.

---

## 10. Self-check before you report

**Transcript**
- [ ] `verified: pass`, and the second pass was actually done segment by segment
- [ ] `term_fixes` lists every proven change; every unproven one is marked inline

**Structure**
- [ ] H2 headings identical to the template, all present, empty ones say "None." / "无。"
- [ ] Every H3 is a content title with the hidden time range at the end; no placeholders
- [ ] No timestamp in the prose, no time column in tables
- [ ] No raw-transcript block anywhere; one body per section
- [ ] No `�`
- [ ] Every embedded image is in the attachments folder and its text is in the prose

**Content**
- [ ] Declaration on the first body line; no "the instructor"/「讲师」 in the body
- [ ] Time order throughout; no topic-grouped sections
- [ ] The only omissions are §2 repetitions and greetings, each with its one-line marker
- [ ] Closing summary verbatim; plan tables complete (sets, reps, rest, RPE, cues)
- [ ] Qualifiers kept, ranges kept, contradictions recorded twice and listed in `gaps`
- [ ] Quotes are verbatim
- [ ] No evaluation, correction, supplement or overview; the note does not restate this spec

**Report** back to the caller: characters written, number of stamped sections, images embedded,
segments added in the second pass, corrections logged, doubts left inline.
