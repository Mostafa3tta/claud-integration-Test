# maestro-scenario

A [Claude Code](https://claude.com/claude-code) plugin that turns your team's test cases into working [Maestro](https://maestro.mobile.dev) UI tests, one case at a time, and keeps a shared sheet up to date while it works.

You give it the test cases your tester or client wrote, in Excel, Word, CSV, PDF or a Google Sheets / Docs / Drive link. It builds one working sheet with an ID for every case. After that you send an ID and Claude:

1. reads the case and the screens it touches in your code,
2. writes the Maestro flow,
3. runs it on your emulator or simulator,
4. fixes it until it passes twice in a row,
5. writes **Status**, **Maestro file**, **Note** and **Last run** back to that row, live.

It works with Android and iOS apps built with Flutter, React Native (incl. Expo) or native code.

---

## Contents

- [Install](#install)
- [Requirements](#requirements)
- [Quick start](#quick-start)
- [Commands](#commands)
- [What setup asks and stores](#what-setup-asks-and-stores)
- [The working sheet](#the-working-sheet)
- [What happens when you run a case](#what-happens-when-you-run-a-case)
- [Google Sheet or local file](#google-sheet-or-local-file)
- [Supported test-case formats](#supported-test-case-formats)
- [Test IDs](#test-ids)
- [Sharing with your team](#sharing-with-your-team)
- [Troubleshooting](#troubleshooting)
- [بالعربي](#بالعربي)

## Install

Inside Claude Code (2.1.275 or later), in any project:

```
/plugin install maestro-scenario --marketplace Mostafa3tta/claud-integration-Test
```

On older versions, add the marketplace first, then install:

```
/plugin marketplace add Mostafa3tta/claud-integration-Test
/plugin install maestro-scenario@mostafa3tta
```

**Without the plugin system:** copy `skills/maestro-scenario/` into your project's `.claude/skills/`. The skill works the same; you just won't have the `/maestro-scenario:*` commands, so ask in plain words instead ("set up maestro-scenario", "run TC-012").

## Requirements

| Needed for | What |
|---|---|
| Everything | Claude Code, Python 3.9+, git |
| Reading `.xlsx` and the local sheet | `python3 -m pip install --user openpyxl` (setup offers to do it) |
| Running tests | [Maestro CLI](https://maestro.mobile.dev/getting-started/installing-maestro) and Java 17+ |
| Android | Android SDK (`adb`) and an emulator or device with your test build installed |
| iOS | Xcode with a booted simulator that has your test build installed |
| Google Sheet mode | Google Chrome with the [Claude in Chrome](https://claude.com/chrome) extension, signed in to the Google account that owns the sheet. Connect it in Claude Code with `/chrome` |

Without Chrome, everything works with a local `.xlsx` sheet in your repo instead.

## Quick start

```
/maestro-scenario:setup ~/Downloads/QA-test-plan.xlsx
```

Setup detects your project and asks you to confirm or fill in:

- the framework and the app id
- the build command
- where flows live
- what shows on first launch
- how tests log in

Then it:

1. reads the test cases and gives each one an ID (`TC-001`, `TC-002`, …),
2. compares them with any Maestro flows you already have,
3. offers to look through the app for flows no test case covers,
4. creates the sheet and saves the project config.

Then:

```
/maestro-scenario:run TC-001
```

Watch the row go to **In progress**, then **Passed** (or a clear reason why not). Run cases by ID (`TC-012`, `tc12`), by name (`"login wrong password"`) or by row number (`25`).

To try it before using your own files, run setup on [`examples/sample-test-cases.csv`](examples/sample-test-cases.csv).

## Commands

| Command | Does |
|---|---|
| `/maestro-scenario:setup [file or link]` | First-time setup: config, sheet, IDs |
| `/maestro-scenario:run <ID \| name \| row>` | Write, run and fix the flow for one case, and update its row |
| `/maestro-scenario:import [file or link]` | Add more test cases to the existing sheet |

You can also just talk to it: "set up Maestro tests from this file", "اعمل تيست TC-12", "run row 30". The skill triggers by itself.

## What setup asks and stores

Everything specific to the project goes into **`.claude/maestro-scenario.json`** in your repo. The plugin itself stays the same for every project.

| Key | Example |
|---|---|
| `project` | name, framework, platforms (`android`, `ios`) |
| `app.<platform>` | app id, build command, install command |
| `flows` | flows folder, the steps every flow starts with, where test accounts come from |
| `test_ids` | how your code gives elements IDs, and the constants file if you have one |
| `sheet` | mode (`google` or `local`), spreadsheet id and link, tab, header row |
| `ids` | ID prefixes (`TC`, `M`, …) and the next number for each, so IDs never repeat |
| `sources` | every file or link imported, with how many cases it gave |

Passwords are never stored there. Flows log in through a login subflow that uses a **test** account.

## The working sheet

A title and live counters at the top, then one row per test case:

| Column | Filled by | Meaning |
|---|---|---|
| ID | setup | `TC-001`… unique, never reused |
| Source | setup | which document (or "Code analysis") the case came from |
| Module, Test Case, Type, Priority | setup | from your document; Type/Priority are inferred if missing (marked in Known issues) |
| Steps, Expected Result | setup | your document's wording; `Pre:` = preconditions |
| Test IDs in code, Screen / file in code | setup / run | where to start in the code |
| Source YAML | setup | an older flow to port, if there is one |
| Known issues | setup | corrections and traps; wins over Steps when they disagree |
| **Status** | run | see below |
| **Maestro file** | run | the flow it wrote |
| **Note** | run | what it asserts, or what went wrong and what's needed |
| **Last run** | run | date |

| Status | Meaning |
|---|---|
| To do | not started |
| In progress | Claude is working on it right now |
| Passed | the flow passed twice in a row |
| Covered – existing flow | setup matched a flow you already had; run the ID to verify it |
| Failed – app bug | the app doesn't do what the Expected Result says; the test stays honest and keeps failing until the bug is fixed |
| Blocked – needs test ID | an element can't be selected reliably; Claude asks before adding an ID to your code |
| Blocked – data | the case needs data your test environment doesn't have |

## What happens when you run a case

- **It works on its own.** It only stops to ask before changing your app's code (adding a test ID), before uninstalling the app, or when a name matches several cases.
- **It reads before it writes.** It reads your screens and your existing passing flows first, so it guesses less and copies your team's patterns (logins, waits, subflows).
- **It diagnoses failures.** On each failure it looks at the screenshot and the elements actually on screen, then decides whether the test, the app or the data is at fault.
- **It won't fake a pass.** It never weakens an assertion to make a test pass. Before marking a case Passed, it checks the flow for the usual ways tests lie: `assertTrue: ${a = b}` (always true), commented-out or optional assertions, and hard-coded test data.
- **It gives up honestly.** It stops after 6 runs without progress and records where it's stuck.
- **It never commits.** You review and commit.

## Google Sheet or local file

| | Google Sheet | Local `.xlsx` |
|---|---|---|
| Needs | Chrome + Claude in Chrome extension | nothing extra |
| Created by | setup, in your Google Drive | setup, in your repo (e.g. `maestro/test-cases.xlsx`) |
| Team sees results | live | after you commit |
| Status dropdown | typed values | built-in dropdown |

The sheet is read and written through your own signed-in Chrome, so it can stay private. Claude only reads the row it needs, and writes only that row's last four cells.

## Supported test-case formats

`.xlsx`, `.csv`, `.tsv`, `.docx`, `.md`, `.txt`, `.pdf` and images, plus Google Sheets, Google Docs and Google Drive file links. Older formats (`.xls`, `.doc`, `.numbers`, `.pages`) need exporting to one of these first.

Any layout works, whether that's one table, many tabs, or numbered steps in Word. Claude normalizes it to one row per case and keeps the author's wording.

## Test IDs

Maestro is most reliable when elements have IDs. See [`skills/maestro-scenario/references/test-ids.md`](skills/maestro-scenario/references/test-ids.md):

| Framework | Gives an element an ID with |
|---|---|
| Flutter | `Semantics(identifier: …)` |
| React Native | `testID` |
| Android | `android:id` / `Modifier.testTag` + `testTagsAsResourceId` |
| iOS | `accessibilityIdentifier` |

## Sharing with your team

Commit `.claude/maestro-scenario.json` (and the workbook, in local mode). Everyone who installs the plugin then works on the same sheet with the same settings.

To set up another project, run `/maestro-scenario:setup` there.

## Troubleshooting

| Problem | Fix |
|---|---|
| "No config" | Run `/maestro-scenario:setup` in the project root |
| The sheet can't be read | Connect Chrome with `/chrome`. The first time, Chrome asks to allow multiple downloads: click Allow |
| A Google link opens a sign-in page | Share the file with the Google account signed in to Chrome, or download it and pass the path |
| "Expected exactly one connected device" | Start one emulator/simulator, or pass the device id |
| `openpyxl` not found | `python3 -m pip install --user openpyxl` |
| Install fails with a signature mismatch after adding a test ID | The installed build was signed differently. Uninstalling wipes the app's data on that device; Claude asks before doing it |
| Clipboard step fails (Windows) | Setup gives you the `.xlsx`: upload it to Google Drive → Open with Google Sheets, and send the link |

---

## بالعربي

**الـ plugin دي بتعمل إيه؟** بتاخد الـ test cases اللي كتبها التيستر أو الكلاينت، بأي شكل: Excel، أو Word، أو PDF، أو لينك Google. وبتعمل منها شيت فيه ID لكل test case. بعد كده تبعت ID، وClaude يكتب تيست Maestro، ويشغّله على الإيميوليتر، ويصلّحه لحد ما ينجح مرتين، ويكتب النتيجة في نفس الصف في الشيت لايف.

**التسطيب** من جوه Claude Code:

```
/plugin install maestro-scenario --marketplace Mostafa3tta/claud-integration-Test
```

**أول مرة في أي مشروع:**

```
/maestro-scenario:setup <مسار ملف الـ test cases أو اللينك>
```

هيسألك سؤال واحد كل مرة: نوع المشروع، و app id، وأمر الـ build، وفين التيستات. وبيحاول يعرف الإجابات لوحده من المشروع، وإنت تأكّد بس. وبعدين يعمل الشيت ويحفظ كل الإعدادات في `.claude/maestro-scenario.json`.

**بعد كده:**

```
/maestro-scenario:run TC-001
```

**مش بيسألك غير** قبل ما يعدّل في كود التطبيق (لما يحتاج يضيف test ID)، أو قبل ما يمسح التطبيق من الجهاز.

**لو التطبيق نفسه فيه bug**، مش بيلف حواليه عشان التيست ينجح. بيكتب `Failed – app bug` وجنبه السبب.

**عشان الفريق كله يشتغل على نفس الشيت:** اعمل commit لملف `.claude/maestro-scenario.json`.

## License

[MIT](LICENSE)
