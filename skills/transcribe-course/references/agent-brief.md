# Brief for the writing agent — fill every `{…}` and send it verbatim

The writing agent only sees this brief, the spec, the template and the files listed below. Absolute
paths everywhere: the agent has no idea where the workspace is unless you tell it. Keep the wording;
it encodes lessons from earlier runs (every rule below was added after a draft broke it).

```
Turn the video {stem} into a verbatim-level note.
Workspace root: {absolute workspace path}. Every path below is relative to it unless absolute.

Rules
- Spec: {absolute path to references/SPEC.md} — read it end to end first, then follow it.
- Template: {absolute path to the template file, e.g. templates/zh/lecture.md or the workspace override}.
  Second-level headings verbatim, in order, all present. Blockquote lines under headings are instructions, not content.
- Flavor: {obsidian | markdown}. Embeds: {`![[file.jpg]]` | `![label](attachments/file.jpg)`}.
  Section time ranges: {`### Title %%mm:ss–mm:ss%%` | `### Title <!-- mm:ss–mm:ss -->`}.

Inputs
- Transcript: transcripts/{stem}.txt (primary, read in order); transcripts/{stem}.json (second pass).
- Frame list: frames/{stem}/framelist.md. Frames that go into the note are already in notes/attachments/;
  embed by file name only. Other candidates are in frames/{stem}/ if you need a closer look.
- Whisper model: {model}. The transcript still has homophone errors. Change a word ONLY when the screen,
  a burned-in subtitle, or this table proves it:
  {your correction table, one per line: wrong → right (source)}

Correction conventions (spec §4)
- Proven change: write the corrected word in the prose, no bracket; log once in frontmatter
  `term_fixes: "wrong→right×count, …"` (before `gaps:`).
- Not proven: keep the original word and add {`[转写存疑，疑为"X"]` | `[unclear, possibly "X"]`}. Do not substitute a guess.
- `�` characters: fill from context, log as {`转写乱码→X` | `garbled→X`}, never copy `�` into the note.
- Tables, percentages and ranges printed on slides go into the prose of the matching time range word for word,
  including what was not read aloud — the numbers on the slides are the main content of this kind of lesson.

Lesson facts
- Type: {lecture | technique}. Title on the title slide / in the opening: "{title}".
- Length {mm:ss}. source_file: {stem}{ext}. whisper_model: {model}. modality: {video | audio_only}. course: {course name}.
- Structure by the contact sheets: {mm:ss–mm:ss page/segment X; …}
- Plan / protocol shown: {"none in this lesson" | "yes: sets/reps/rest on screen at mm:ss, RPE spoken" | "named but not given: write 'not given'"} — do not fill from anywhere else.

Output
- Write exactly one file: {absolute path to notes/{stem}{suffix}.md}. Do not read or modify any other note.
- Length: whatever covers the transcript; do not pad.
- Report back: characters written, stamped sections, images embedded, segments added in the second pass,
  corrections logged in term_fixes, doubts left inline (with their mm:ss from the transcript).
```

## Filling notes

- **Correction table**: only entries you can defend from the title slide, a frame you read, the subtitle
  strips, or a term that cannot be anything else. Two or three entries are normal; zero is fine.
- **Structure**: give the agent the page boundaries you saw on the contact sheets ("00:00–00:27 title page,
  00:28–02:15 slide 'Why periodise', …"). It writes faster and sections land on the right ranges.
- **Plan / protocol**: say explicitly whether the video shows one. Left unsaid, the agent may reconstruct a
  plan from the lecture examples.
- **Suffix**: name the draft `{stem}_draft.md` (or `_sonnet` / `_careful` when comparing agents); the final
  name is decided when the note is accepted.
- **Type**: lecture = slides + speech, may end with summary and plan; technique = one movement or protocol
  demonstrated, 2–8 minutes. Anything else: pick the closer one, or add a template to the workspace.
