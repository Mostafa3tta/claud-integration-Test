---
description: Write, run and fix the Maestro flow for one test case from the sheet, by ID, name or row number
argument-hint: "<ID | test name | row number>"
---

Use the maestro-scenario skill to automate this test case: $ARGUMENTS

Follow the skill's "Run a test case" workflow: fetch the row, mark it In progress, write the flow, run it until it passes twice, then write the result back to the sheet.

If no case was given, show the sheet link and ask which case to run. If the project has no `.claude/maestro-scenario.json` yet, say the project needs setting up first and start the setup.
