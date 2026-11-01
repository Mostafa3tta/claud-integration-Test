---
description: Add more test cases to this project's sheet from another file or link
argument-hint: "[path or link to the new test cases]"
---

Use the maestro-scenario skill to import more test cases into this project's existing sheet. Follow `references/setup.md` → "Re-running parts later" → "Import more test cases": steps 3–6 for the new source, then append the rows.

New test cases: $ARGUMENTS
If that's empty, ask for the file or link.

If the project has no `.claude/maestro-scenario.json` yet, run the full setup instead.
