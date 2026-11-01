#!/usr/bin/env python3
"""Build the working sheet from normalized test cases.

Input is a JSON list of test cases (see references/setup.md for the fields).
Cases without an "id" get the next ID for --prefix from the project config,
and the config counter moves on, so IDs never repeat across imports.

Outputs, by --out:
  xlsx    a complete workbook (title, live counters, header, rows, Status
          dropdown, filter). For local mode, or to upload to Google Drive.
  html    the same layout as HTML + TSV for pasting into a new, empty Google
          Sheet at A1 (see set_clipboard.py).
  rows    data rows only, as HTML + TSV, for pasting under the last row of an
          existing sheet.
  append  data rows appended to an existing local workbook (--xlsx PATH).

Usage:
  build_sheet.py cases.json --prefix TC --out xlsx --xlsx maestro/test-cases.xlsx
  build_sheet.py cases.json --prefix TC --out html --dest /tmp/sheet
  build_sheet.py cases.json --prefix TC --out rows --dest /tmp/rows
  build_sheet.py cases.json --prefix TC --out append --xlsx maestro/test-cases.xlsx
  build_sheet.py --assigned cases.json ...   (print the cases with their IDs, no output)
"""
import argparse
import html
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfgmod  # noqa: E402

HEADERS = ["ID", "Source", "Module", "Test Case", "Type", "Priority", "Steps",
           "Expected Result", "Test IDs in code", "Screen / file in code",
           "Source YAML", "Known issues", "Status", "Maestro file", "Note", "Last run"]
FIELDS = ["id", "source", "module", "title", "type", "priority", "steps",
          "expected", "test_ids", "screen", "source_yaml", "known_issues",
          "status", "maestro_file", "note", "last_run"]
WIDTHS = [10, 22, 18, 34, 10, 10, 48, 40, 30, 30, 26, 34, 22, 30, 40, 12]
STATUSES = [
    ("To do", "FFFFFF", "Not started"),
    ("In progress", "CFE2F3", "The maestro-scenario skill is working on it right now"),
    ("Passed", "B7E1CD", "Flow passes twice in a row; file in the flows folder (see Maestro file)"),
    ("Covered – existing flow", "D9D2E9", "An existing flow seems to cover it; run the skill on the ID to verify"),
    ("Failed – app bug", "F4C7C3", "The app does not match the Expected Result; details in Note"),
    ("Blocked – needs test ID", "FCE8B2", "An element has no test ID; waiting for approval to add one (see Note)"),
    ("Blocked – data", "FCE8B2", "The data the scenario needs is not available (see Note)"),
]
PRIORITY_FILL = {"High": "F4CCCC", "Medium": "FFF2CC", "Low": "D9EAD3"}
HEADER_FILL = "1F3864"
# Layout of a sheet built by this script: title, note, blank, counters from
# row 4, one blank row, then the header. The counters block grows with the
# number of sources, so the header row is computed (14 with up to 7 sources).
TITLE_ROW, SUMMARY_ROW = 1, 4
LAST_FORMULA_ROW = 2000


def layout(cfg):
    sources = len(cfg.get("sources", [])) or 1
    block = max(len(STATUSES), sources) + 1          # rows under the counters header
    header_row = SUMMARY_ROW + block + 2
    return header_row, header_row + 1


def col_letter(index):  # 1-based
    s = ""
    while index:
        index, r = divmod(index - 1, 26)
        s = chr(65 + r) + s
    return s


STATUS_COL = col_letter(HEADERS.index("Status") + 1)   # M
SOURCE_COL = col_letter(HEADERS.index("Source") + 1)   # B


def load_cases(path, prefix, cfg):
    with open(path, encoding="utf-8") as f:
        cases = json.load(f)
    assigned = 0
    for case in cases:
        if not case.get("id"):
            if not prefix:
                sys.exit("Some cases have no id: pass --prefix")
            case["id"] = cfgmod.reserve_id(cfg, prefix)
            assigned += 1
        case.setdefault("status", "To do")
        for key in FIELDS:
            case.setdefault(key, "")
    return cases, assigned


def summary_rows(cfg):
    """Rows for the counters block: (A,B,C) status counters, (E,F) per source."""
    sources = [s["name"] for s in cfg.get("sources", [])] or ["(no sources yet)"]
    _, first = layout(cfg)
    rows = []
    for i in range(max(len(STATUSES) + 1, len(sources) + 1)):
        r = SUMMARY_ROW + 1 + i
        left = right = None
        if i < len(STATUSES):
            name, fill, meaning = STATUSES[i]
            left = (name, f"=COUNTIF(${STATUS_COL}${first}:${STATUS_COL}${LAST_FORMULA_ROW},A{r})", meaning, fill)
        elif i == len(STATUSES):
            left = ("Total", f"=SUM(B{SUMMARY_ROW + 1}:B{r - 1})", "", None)
        if i < len(sources):
            right = (sources[i], f"=COUNTIF(${SOURCE_COL}${first}:${SOURCE_COL}${LAST_FORMULA_ROW},E{r})")
        elif i == len(sources):
            right = ("Total", f"=SUM(F{SUMMARY_ROW + 1}:F{r - 1})")
        rows.append((left, right))
    return rows


# ---------- xlsx ----------

def write_xlsx(cases, cfg, path, append=False):
    try:
        import openpyxl
        from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
        from openpyxl.worksheet.datavalidation import DataValidation
    except ImportError:
        sys.exit("openpyxl is needed: python3 -m pip install --user openpyxl")

    tab = cfgmod.get(cfg, "sheet.tab") or "All Test Cases"
    font = lambda **kw: Font(name="Arial", size=kw.pop("size", 10), **kw)  # noqa: E731
    thin = Side(style="thin", color="D0D5DD")
    border = Border(top=thin, bottom=thin, left=thin, right=thin)
    wrap = Alignment(vertical="top", wrap_text=True)

    if append:
        wb = openpyxl.load_workbook(path)
        ws = wb[tab]
        header_row = cfgmod.get(cfg, "sheet.header_row") or layout(cfg)[0]
        row = ws.max_row + 1
        while row > header_row + 1 and not ws.cell(row - 1, 1).value:
            row -= 1
    else:
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = tab
        project = cfgmod.get(cfg, "project.name") or "App"
        ws.cell(TITLE_ROW, 1, f"{project} – test cases to automate with Maestro").font = font(size=14, bold=True)
        ws.cell(TITLE_ROW + 1, 1,
                "Give the maestro-scenario skill an ID, a test name or a row number; it writes "
                "Status, Maestro file, Note and Last run on that row.").font = font(size=9, italic=True, color="666666")
        for c, label in ((1, "Status"), (2, "Count"), (3, "Meaning"), (5, "Source"), (6, "Count")):
            cell = ws.cell(SUMMARY_ROW, c, label)
            cell.font = font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
        for i, (left, right) in enumerate(summary_rows(cfg)):
            r = SUMMARY_ROW + 1 + i
            if left:
                name, formula, meaning, fill = left
                a = ws.cell(r, 1, name)
                a.font = font(bold=True)
                if fill:
                    a.fill = PatternFill("solid", fgColor=fill)
                ws.cell(r, 2, formula).alignment = Alignment(horizontal="center")
                ws.cell(r, 3, meaning).font = font()
            if right:
                ws.cell(r, 5, right[0]).font = font(bold=right[0] == "Total")
                ws.cell(r, 6, right[1]).alignment = Alignment(horizontal="center")
        header_row, first_row = layout(cfg)
        for c, label in enumerate(HEADERS, 1):
            cell = ws.cell(header_row, c, label)
            cell.font = font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            ws.column_dimensions[col_letter(c)].width = WIDTHS[c - 1]
        row = first_row

    for case in cases:
        for c, key in enumerate(FIELDS, 1):
            cell = ws.cell(row, c, case.get(key, ""))
            cell.font = font(bold=(key == "id"))
            cell.alignment = wrap
            cell.border = border
            if key == "priority" and case.get(key) in PRIORITY_FILL:
                cell.fill = PatternFill("solid", fgColor=PRIORITY_FILL[case[key]])
        row += 1
    last = row - 1

    status_col = HEADERS.index("Status") + 1
    ws.data_validations.dataValidation = [
        dv for dv in ws.data_validations.dataValidation if col_letter(status_col) not in str(dv.sqref)
    ]
    dv = DataValidation(type="list", allow_blank=True,
                        formula1='"' + ",".join(s[0] for s in STATUSES) + '"')
    ws.add_data_validation(dv)
    dv.add(f"{col_letter(status_col)}{header_row + 1}:{col_letter(status_col)}{max(last, header_row + 1) + 200}")
    ws.auto_filter.ref = f"A{header_row}:{col_letter(len(HEADERS))}{max(last, header_row + 1)}"
    wb.save(path)
    return path, last


# ---------- html / tsv for Google Sheets ----------

F = "font-family:Arial;font-size:10pt;vertical-align:top;"
H = f"background:#{HEADER_FILL};color:#ffffff;font-weight:bold;" + F


def td(value, style=F):
    return f'<td style="{style}">{html.escape(str(value)).replace(chr(10), "<br>")}</td>'


def row_html(case):
    cells = []
    for key in FIELDS:
        v = case.get(key, "")
        style = F
        if key == "id":
            style += "font-weight:bold;text-align:center;"
        if key == "priority" and v in PRIORITY_FILL:
            style += f"background:#{PRIORITY_FILL[v]};font-weight:bold;text-align:center;"
        if key in ("type", "status"):
            style += "text-align:center;"
        if key in ("screen", "source_yaml"):
            style += "font-size:9pt;color:#555555;"
        if key == "known_issues" and v:
            style += "color:#B45F06;"
        cells.append(td(v, style))
    return "<tr>" + "".join(cells) + "</tr>"


def full_html(cases, cfg):
    project = cfgmod.get(cfg, "project.name") or "App"
    header_row, _ = layout(cfg)
    rows = [
        td(project + " – test cases to automate with Maestro", "font-family:Arial;font-size:14pt;font-weight:bold"),
        td("Give the maestro-scenario skill an ID, a test name or a row number; it writes Status, "
           "Maestro file, Note and Last run on that row.",
           "font-family:Arial;font-size:9pt;font-style:italic;color:#666666"),
        "<td></td>",
        f'{td("Status", H)}{td("Count", H)}{td("Meaning", H)}<td></td>{td("Source", H)}{td("Count", H)}',
    ]
    for left, right in summary_rows(cfg):
        cells = ""
        if left:
            name, formula, meaning, fill = left
            cells += td(name, F + "font-weight:bold;" + (f"background:#{fill};" if fill else ""))
            cells += f'<td style="{F}text-align:center">{formula}</td>' + td(meaning)
        else:
            cells += "<td></td><td></td><td></td>"
        cells += "<td></td>"
        if right:
            cells += td(right[0], F + ("font-weight:bold;" if right[0] == "Total" else ""))
            cells += f'<td style="{F}text-align:center">{right[1]}</td>'
        rows.append(cells)
    while len(rows) < header_row - 1:
        rows.append("<td></td>")
    rows.append("".join(td(h, H) for h in HEADERS))
    body = "".join(f"<tr>{r}</tr>" for r in rows) + "".join(row_html(c) for c in cases)
    return f'<meta charset="utf-8"><table>{body}</table>'


def tsv(cases):
    return "\n".join("\t".join(str(c.get(k, "")).replace("\n", " ").replace("\t", " ") for k in FIELDS) for c in cases)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cases")
    ap.add_argument("--prefix")
    ap.add_argument("--out", choices=["xlsx", "html", "rows", "append"])
    ap.add_argument("--xlsx", help="workbook path for xlsx / append")
    ap.add_argument("--dest", help="file prefix for html / rows output (writes .html and .tsv)")
    ap.add_argument("--assigned", action="store_true", help="assign IDs and print the cases only")
    args = ap.parse_args()

    cfg = cfgmod.load()
    cases, assigned = load_cases(args.cases, args.prefix, cfg)
    with open(args.cases, "w", encoding="utf-8") as f:   # keep the IDs that were given out
        json.dump(cases, f, indent=2, ensure_ascii=False)
    if assigned:
        cfgmod.save(cfg)

    if args.assigned or not args.out:
        print(json.dumps([{"id": c["id"], "title": c["title"]} for c in cases], ensure_ascii=False, indent=1))
        return
    if args.out in ("xlsx", "append"):
        if not args.xlsx:
            sys.exit("--xlsx PATH is required")
        path, last = write_xlsx(cases, cfg, args.xlsx, append=args.out == "append")
        print(json.dumps({"workbook": path, "rows": len(cases), "last_row": last,
                          "header_row": cfgmod.get(cfg, "sheet.header_row") if args.out == "append" else layout(cfg)[0],
                          "first_row": cfgmod.get(cfg, "sheet.first_row") if args.out == "append" else layout(cfg)[1],
                          "ids_assigned": assigned}))
    else:
        if not args.dest:
            sys.exit("--dest PREFIX is required")
        content = full_html(cases, cfg) if args.out == "html" else \
            '<meta charset="utf-8"><table>' + "".join(row_html(c) for c in cases) + "</table>"
        with open(args.dest + ".html", "w", encoding="utf-8") as f:
            f.write(content)
        with open(args.dest + ".tsv", "w", encoding="utf-8") as f:
            f.write(tsv(cases))
        print(json.dumps({"html": args.dest + ".html", "tsv": args.dest + ".tsv", "rows": len(cases),
                          "header_row": layout(cfg)[0], "first_row": layout(cfg)[1], "ids_assigned": assigned}))


if __name__ == "__main__":
    main()
