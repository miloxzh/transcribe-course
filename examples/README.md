# Examples

`en/` holds a small synthetic English lesson — a transcript in the format `tc.py transcribe` writes and a
finished note in the `lecture` template — so you can watch the gate work before transcribing anything:

```bash
python skills/transcribe-course/scripts/tc.py init /tmp/tc-demo --preset generic-en
python skills/transcribe-course/scripts/tc.py check examples/en/L02_shoulder-assessment.json examples/en/L02_shoulder-assessment.md --workspace /tmp/tc-demo
```

Expected: `verify` PASS, coverage 12/12, `GATE PASS`. Now paraphrase one sentence in the note and run it
again: coverage drops to 11/12 and the missed transcript line is printed — that is the check that keeps
the writing agent from summarising.

The content is invented for the example (it is not a real course); real notes look the same but longer,
with embedded frames under the slide text.
