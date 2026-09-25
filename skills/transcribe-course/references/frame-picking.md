# Picking frames and writing `framelist.md`

Frame picking is the one step in the pipeline that needs judgement. The detector gives you
candidates and contact sheets; you decide what a reader would lose without seeing it.

## The test

**If the reader does not see this frame, do they lose information?**

| Keep | Drop |
|---|---|
| Tables, charts, curves, diagrams, anatomy drawings on slides | Frames that only show the speaker |
| Lists with numbers: grades, ranges, percentages, doses, weeks | Slides with nothing but a title (copy the title into the prose) |
| Every plan / protocol / prescription table | A frame identical to the previous one (animation steps: keep the last, complete state) |
| Demo videos: angles drawn on screen, equipment settings, "wrong vs right" comparisons | Ordinary demo shots (their burned-in subtitles still go in the evidence table) |
| Assessment sheets, scoring rubrics, anything the reader might want to reproduce | Transition frames caught mid-animation |

For a slide lecture, nearly every slide except the title and closing pages is a text-and-numbers
page: expect to keep most of them. For a demo video, expect 2–6 frames.

## How to look

1. Open every `_sheet_N.jpg` (and `_overview_N.jpg` if you made them) with Read. The label on each
   tile is `mm:ss  detector  filename`.
2. When small text is unreadable on the sheet, open the candidate file itself.
3. Few candidates on a long video does **not** mean "no slides". Dark themes with small text can
   defeat the default threshold; rerun `frames --frac 0.005` and look again before concluding.
4. Something you need is not among the candidates (an overlay that shows for half a second, a page
   the detector merged)? `tc.py grab <video> mm:ss` fetches any moment at full resolution; add 0.5 s if
   the overlay is not there yet.

## Attach with the convention

```
python tc.py attach {stem} 01:43 core-principles --prefix D29
→ notes/attachments/D29_0143_core-principles.jpg    embed: ![[D29_0143_core-principles.jpg]]
```
Prefix = the lecture code (`D29`, `L03`) or the technique name; label = a few words, no spaces.
The `mmss` in the file name is the only time reference allowed outside the hidden section comments.

## `frames/{stem}/framelist.md`

Two tables. The writing agent reads this file, then opens every listed image itself; your text is an
index that tells it what to look for, not a transcription.

```markdown
# {stem} — frame list

Video {stem}.mp4, 18:54. Title slide: "Sliding filaments — the mechanism of contraction" (Day 8).

## 1. Frames that go into the note (already in notes/attachments/, embed by file name, text first then image)

| Time | Attachment | What is on it (index; the agent reads the original) |
|---|---|---|
| 00:18 | `D08_0018_sarcomere.jpg` | Title "Basic sarcomere structure". Labels: Z line, I band, A band, M line, H zone, thick/thin filament. Caption at the bottom. |
| 02:39 | `D08_0239_crossbridge-cycle.jpg` | Four panels: binding / power stroke / detachment (ATP) / reset. Legend mentions Ca²⁺. |
| 06:29 | `D08_0629_key-points.jpg` | The course's own "Key points" page, four items with small print — **the small print goes verbatim into the takeaways section**. |

Notes: 00:00 is the title page (text: "…") — not embedded, its text goes into the opening section.
03:23 repeats the 02:39 diagram; not embedded twice.

## 2. Evidence-only frames (in frames/{stem}/, open as needed; not embedded)

From 12:31 the men's plan is demonstrated; 16:04 "class over" page; then the women's plan.

| Time | File | Burned-in subtitle | Screen |
|---|---|---|---|
| 12:31 | D08_1231 | straight-arm pulldown | cable straight-arm pulldown demo |
| 13:17 | D08_1317 | ten to fifteen degrees | lat pulldown |
| 15:36 | D08_1536 | RPE set to eight | bent-over fly |

06:29–12:31 has no screen change (about six minutes on the key-points page); that stretch relies on the transcript alone.
```

The evidence table is worth the typing: the burned-in subtitles are the spelling the editor
proofread, and the writing agent uses them to fix homophones without guessing.
