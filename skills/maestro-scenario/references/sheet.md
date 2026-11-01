# The working sheet: reading and writing a row

Everything about where the sheet is comes from the config: `scripts/config.py get sheet` (`mode`, `spreadsheet_id`, `tab`, `gid`, `header_row`, `first_row`, `write_columns`, `local_path`). Rows above `header_row` are a title and counters with formulas, so never edit them. People sort and filter the table, so a row number is only good until the next fetch; always fetch before writing.

## Columns

| Header | Meaning |
|---|---|
| ID | `<PREFIX>-<number>`, unique; prefixes and their meaning are in config `ids` |
| Source | which document or analysis the case came from |
| Module, Test Case, Type, Priority | as given by the source (Type/Priority may be inferred, see Known issues) |
| Steps | `Pre: …` on the first line = preconditions |
| Expected Result | what the flow must assert |
| Test IDs in code | IDs to start from; `⚠ no test ID` = the element has none |
| Screen / file in code | where to read the screen first |
| Source YAML | an older flow to port, if any |
| Known issues | corrections and traps; wins over Steps / Expected Result |
| **Status** | written by the skill |
| **Maestro file** | written by the skill |
| **Note** | written by the skill |
| **Last run** | written by the skill (`YYYY-MM-DD`) |

Status values. The counters match these exact strings, en dash included, so write them exactly:

| Status | When |
|---|---|
| `To do` | not started |
| `In progress` | set at the start of a run, so people watching see it |
| `Passed` | passed twice in a row |
| `Covered – existing flow` | setup matched an existing flow; not run by the skill yet |
| `Failed – app bug` | the app doesn't do what the Expected Result says |
| `Blocked – needs test ID` | an element has no test ID and adding one isn't approved yet |
| `Blocked – data` | the data the case needs isn't available |

Older sheets may lack `Covered – existing flow` in their counters; writing it is still fine.

## Google mode (through the user's Chrome)

The sheet is private, so it's read and written through the Claude in Chrome tools, signed in as the user. The Google Drive connector's `read_file_content` returns only a sample of rows, so it can't find a specific row.

### Fetch

1. In a new tab of the Claude in Chrome tab group, open the tab's CSV export (URL-encode the tab name, spaces as `%20`):

   ```
   https://docs.google.com/spreadsheets/d/<spreadsheet_id>/gviz/tq?tqx=out:csv&sheet=<tab>&range=A<header_row>:<last_col>2000&headers=1
   ```

   Chrome downloads it as `~/Downloads/data.csv` (or `data (1).csv`) instead of showing a page; that's expected, so don't call `get_page_text`. The first time, Chrome may ask to allow multiple downloads; ask the user to click Allow.

2. Pick the row:

   ```bash
   python3 <skill-dir>/scripts/fetch_row.py --key TC-012     # or M-05, "tc12"
   python3 <skill-dir>/scripts/fetch_row.py --key "Login wrong password"
   python3 <skill-dir>/scripts/fetch_row.py --row 25
   ```

   It moves the newest download out of `~/Downloads` and prints JSON: `sheet_row`, the cells by header, and `other_matches` when a name matched several rows. Only that row reaches the context.

### Write

Select the Status cell by URL, then type across the row. Tab moves one cell to the right without changing a cell you don't type in.

```
https://docs.google.com/spreadsheets/d/<spreadsheet_id>/edit#gid=<gid>&range=<write_columns.status><sheet_row>
```

1. Navigate, wait about 3 seconds, zoom on the Name box at the top-left and check that it shows the right cell. Select by URL, not by clicking: the window gets resized and coordinates drift.
2. **Start of a run:** type `In progress`, then `Return`.
3. **End of a run:** select the Status cell again, then type Status `Tab` Maestro file `Tab` Note `Tab` date `Return`.
   - This assumes the four write columns are adjacent (`write_columns` M, N, O, P).
   - If they aren't, select and type each cell by its own URL.
4. Fetch the row again and check two things: the written cells hold what you typed, **and** the ID column still shows the case's ID. If the values landed on another row, restore that row's old values (from the first fetch) and tell the user.

## Local mode (an .xlsx in the repo)

### Fetch

`fetch_row.py --key … / --row …` reads `sheet.local_path` directly; there's nothing to download.

### Write

```bash
python3 <skill-dir>/scripts/write_row.py --row <sheet_row> --id <ID> --status "In progress"
python3 <skill-dir>/scripts/write_row.py --row <sheet_row> --id <ID> --status Passed \
  --file maestro/TC-012-login-wrong-password.yaml --note "Asserts error text and that Login stays open"
```

The script refuses to write if that row doesn't hold `<ID>` (the sheet was sorted: fetch again). It also refuses if the workbook is open in Excel, because Excel would overwrite the change when it saves; ask the user to close it.

## Note text

- One or two sentences, in the sheet's language (English unless the team chose otherwise).
- Start with a letter, never `=`, `+`, `-` or `@`, because Sheets reads those as formulas. Separate parts with ` | ` instead of new lines.
- **Passed:** what the flow asserts, and anything worth knowing. Example: `Asserts sort order for price asc/desc and that the choice is kept | results need up to 30s`
- **Failed or Blocked:** what happened, where, and what's needed. Example: `No error after a wrong password; Login stays empty | login_screen.dart never shows loginErrorKey`

Don't touch the rows above the header, the header itself, or any row except the case's own.
