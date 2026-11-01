#!/usr/bin/env python3
"""Write a run's result into the local working sheet (local mode only).

Google mode is written through Chrome instead (references/sheet.md → Write).
Only the Status, Maestro file, Note and Last run cells of one row change, and
only after checking that the row still holds the expected ID, so a sorted or
edited sheet can't receive another case's result.

Usage:
  write_row.py --row 25 --id TC-012 --status "In progress"
  write_row.py --row 25 --id TC-012 --status Passed --file maestro/TC-012-login.yaml \
               --note "Asserts error text and that Login stays open"
"""
import argparse
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfgmod  # noqa: E402

COLUMNS = {"status": "Status", "file": "Maestro file", "note": "Note", "date": "Last run"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--row", type=int, required=True)
    ap.add_argument("--id", required=True, help="the ID this row must hold")
    ap.add_argument("--status", required=True)
    ap.add_argument("--file")
    ap.add_argument("--note")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    args = ap.parse_args()

    cfg = cfgmod.load()
    sheet = cfg.get("sheet", {})
    if sheet.get("mode") != "local":
        sys.exit("The sheet is in google mode: write through Chrome (references/sheet.md → Write).")
    path = os.path.join(cfgmod.repo_root(), sheet["local_path"])
    lock = os.path.join(os.path.dirname(path), "~$" + os.path.basename(path))
    if os.path.exists(lock):
        sys.exit(f"{os.path.basename(path)} is open in Excel. Ask the user to close it first; "
                 "saving from Excel later would overwrite this write.")

    import openpyxl
    wb = openpyxl.load_workbook(path)
    ws = wb[sheet["tab"]]
    header_row = sheet.get("header_row") or sheet.get("first_row", 15) - 1
    header = {str(c.value): c.column for c in ws[header_row] if c.value}
    missing = [h for h in ["ID", *COLUMNS.values()] if h not in header]
    if missing:
        sys.exit(f"Columns {missing} not found in header row {header_row}")

    found = str(ws.cell(args.row, header["ID"]).value or "")
    if found.strip().upper() != args.id.strip().upper():
        sys.exit(f"Row {args.row} holds '{found}', not {args.id}. Fetch the row again; the sheet may have been sorted.")

    ws.cell(args.row, header["Status"], args.status)
    if args.status != "In progress":
        if args.file is not None:
            ws.cell(args.row, header["Maestro file"], args.file)
        if args.note is not None:
            ws.cell(args.row, header["Note"], args.note)
        ws.cell(args.row, header["Last run"], args.date)
    wb.save(path)
    print(f"Row {args.row} ({args.id}) → {args.status}")


if __name__ == "__main__":
    main()
