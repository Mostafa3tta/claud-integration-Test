---
name: maestro-scenario
description: Automate mobile test cases with Maestro from a shared tracking sheet, for any Android or iOS app (Flutter, React Native or native). First run in a project, or "setup" / "import test cases": takes the team's test cases in whatever form they come (Excel, Word, CSV, PDF, Google Sheets / Docs / Drive link, from a tester or the client), builds a working sheet with an ID per case (Google Sheet, or a local .xlsx), compares them with existing flows, can find untested screens in the code, and saves everything in a project config. After that: give it a case by ID ("TC-012", "M-05"), name or sheet row and it writes the Maestro flow, runs it on the emulator or simulator, fixes it until it passes twice, and writes Status and Note back to that row live. Use whenever someone wants to set up Maestro test automation from test cases, import or add test cases, or automate / run / fix a test case from the sheet — "اعمل تيست TC-12", "شغّل الصف 30", "حوّل الـ test cases دي لـ maestro" — even if they don't say "Maestro" or "skill".
---

# Test cases → passing Maestro flows, tracked in one sheet

Teams get test cases from testers or clients in all kinds of files. This skill turns them into one working sheet with an ID per case, then automates each case on request: it writes a Maestro flow, runs it, repairs it until it really passes, and records the result on the case's row. Everything specific to a project (app id, build commands, where the sheet is, ID prefixes) lives in the project's config, so the skill folder itself can be copied unchanged to any repo.

`<skill-dir>` below means this skill's base directory, shown as "Base directory for this skill" when it loads. It's `.claude/skills/maestro-scenario` when the skill is copied into a project, or a folder in the plugin cache when installed as a plugin. Run the scripts from the project root, because they find the project's config through git.

## Start here: which mode?

Find the config first:

```bash
python3 <skill-dir>/scripts/config.py path
```

- **No config** → this project hasn't been set up. Tell the user in one line that you'll set it up first, then follow [references/setup.md](references/setup.md). It asks for what it needs as it goes; at the end the user can give a case ID right away.
- **The user asks to set up again, change a setting, or import / add test cases** → [references/setup.md](references/setup.md) (it has sections for re-running parts).
- **The user gives a case (ID, name or row number)** → the run workflow below.
- **Config exists but no case was given** → show the sheet link (`config.py get sheet.url`, or `sheet.local_path`) and ask which case to run.

Read the config once at the start of a run (`config.py show`). The values named below (`app.<platform>.app_id`, `flows.start_snippet` and so on) come from it.

## Run a test case

The user hands over one case and expects to come back to a passing flow and an updated row, without being asked things along the way. Work on your own; interrupt only for the changes to the app or its data listed in step 6.

A flow that passes because it stopped checking anything is worse than no flow: the sheet would say Passed while the behavior stays untested. Aim for a flow that passes **and** still asserts the case's Expected Result. When the app, not the test, is what keeps it failing, record that honestly instead of bending the test.

### 1. Check the bench

Run these together; if one fails, say what's missing and stop:
- `maestro --version`
- Device:
  - **Android:** `adb devices` shows a device.
  - **iOS:** `xcrun simctl list devices booted` shows a simulator.
  - If more than one is connected, ask once which to use.
- App installed:
  - **Android:** `adb -s <device> shell pm list packages <app_id>`.
  - **iOS:** `xcrun simctl get_app_container <device> <app_id>`.
- Sheet reachable:
  - **Google mode:** the Claude in Chrome tools respond. If not, ask the user to connect Chrome (`/chrome`).
  - **Local mode:** the workbook at `sheet.local_path` exists.

### 2. Fetch the row and mark it In progress

Follow [references/sheet.md](references/sheet.md): fetch, run `scripts/fetch_row.py --key …` or `--row …`, then write `In progress` so the user sees it live. Keep `sheet_row` and the ID; every write checks them.
- A name that matches several rows (`other_matches`) is the one time you ask before starting.
- Status already `Passed`: say so and stop, unless they asked to rerun.
- Status `Covered – existing flow`: the Maestro file column names a flow that probably covers the case. Run that flow (step 5) instead of writing a new one, and extend it only if it misses part of the Expected Result.

**Read Known issues first.** It holds corrections and traps found during setup. Where it contradicts Steps or Expected Result, Known issues wins.

### 3. Learn the screens before writing

Each wrong guess at a selector costs a full run (a minute or more), so read first:
- **Screens in code:** the files in "Screen / file in code". If it's empty, find the screen by its visible texts or route names. Look up how the elements get test IDs; the mechanism and constants file are in `test_ids`, and [references/test-ids.md](references/test-ids.md) has how each framework exposes them to Maestro.
- **Ported cases:** the old flow in "Source YAML", if there is one. It's the starting point; fix its defects while porting (no-op asserts, coordinates, hard-coded data).
- **Existing flows:** one or two passing flows in `flows.dir` that walk the same area, so navigation, waits, logins and subflows match what already works.

### 4. Write the flow

Follow [references/conventions.md](references/conventions.md):
- Start with `flows.start_snippet` (or call the start subflow).
- Name the file by `flows.naming` (default `<flows.dir>/<ID>-<short-kebab-title>.yaml`).
- Put a header comment with the ID, the title and the Expected Result.
- Give every item of the Expected Result at least one assertion that fails if that item stops being true.

### 5. Run

```bash
<skill-dir>/scripts/run_flow.sh <flow.yaml> [device]
```

It prints pass/fail, the failing step with its error, the last steps that worked, and the failure screenshots. Look at the ❌ screenshot with the Read tool to see what was actually on screen.

### 6. Diagnose and fix

While the app is still on the failure screen, `scripts/screen_ids.py [device]` lists the IDs and texts it can target now.

| What you see | Kind | Action |
|---|---|---|
| The element is there under another ID or text, or needs a scroll | Test | Fix the selector or scroll, rerun |
| It appears later, or an animation is still running | Test | `extendedWaitUntil` / `waitForAnimationToEnd` with a timeout (never a fixed sleep), rerun |
| A popup, keyboard or permission dialog covers the target | Test | Dismiss it, rerun |
| The element has no test ID in code | App: missing ID | Ask (below) |
| The app does something other than the Expected Result | App: bug | Record and stop |
| The data the case needs isn't there | Data | Find another route to such data; if none, record and stop |

**Missing test ID: the one thing to ask about**, because it changes app code.
1. Write `Blocked – needs test ID` with a Note naming the element and file.
2. Show the exact change, following `test_ids.pattern` and how nearby widgets do it (adding to `test_ids.constants_file` if there is one).
3. Say the app will be rebuilt and reinstalled with `app.<platform>.build` / `install`.
4. On yes: make the change, rebuild and reinstall, set `In progress` again, and continue.

If the install fails with a signature mismatch, uninstalling first wipes the app's data on the device, so ask before doing it. If the user doesn't want app code touched, a text selector is acceptable; mark it `# TODO: needs test ID` and mention it in the Note.

**Bug.** Keep the honest assertion so the flow fails until the bug is fixed. Write `Failed – app bug` with a Note: the step, what the Expected Result says, what the app did, and the screen's file.

**Data.** Write `Blocked – data` with a Note on what's needed.

**No progress after 6 runs.** Stop. Write the closest status with a Note saying where it's stuck and what was tried; the user often knows something that unblocks it.

### 7. Prove it's stable

Two passes in a row: timing and test data vary, so one pass can be luck.

### 8. Review the flow

Before writing Passed:
- No `assertTrue: ${a = b}`: a single `=` assigns and always passes.
- No commented-out or `optional` assertions.
- No hard-coded counts, prices or names from test data.
- `point:` only with a comment saying why.

### 9. Write the result

Per [references/sheet.md](references/sheet.md) → Write: Status, Maestro file, Note, Last run, then confirm by fetching the row again. Write it for failures and blocks too, so a stale `In progress` doesn't mislead anyone.

### 10. Report in chat

Short, in the user's language:
- Status, and the flow file (plus any app files changed for a test ID)
- What the flow asserts, one line per Expected Result item
- What's left for the user: a bug to file, an ID to approve, a TODO selector

Don't commit unless asked; the team commits with its own message rules. Don't edit other flows to make yours pass.
