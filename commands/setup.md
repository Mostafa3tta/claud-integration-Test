---
description: Set up Maestro test automation in this project from your test cases (Excel, Word, CSV, PDF, or a Google Sheets / Docs / Drive link)
argument-hint: "[path or link to the test cases]"
---

Use the maestro-scenario skill to set up this project. Follow its `references/setup.md` from the beginning.

Test cases given with the command: $ARGUMENTS
If that's empty, ask for them when the setup reaches step 3 ("Get the test cases").

If `.claude/maestro-scenario.json` already exists, this project is already set up. Say so in one line, show the sheet link, and ask whether to import more test cases, change a setting, or redo the setup.
