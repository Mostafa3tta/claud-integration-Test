#!/usr/bin/env python3
"""Pick one test case row out of the project's working sheet.

Where the sheet is comes from the project config (scripts/config.py):
- google mode: the tab is exported by opening its gviz CSV URL in Chrome,
  which drops ~/Downloads/data.csv (references/sheet.md). The newest such
  file is moved out of Downloads and read.
- local mode: the workbook at sheet.local_path is read directly.

Prints the row as JSON with its sheet row number, needed to write back.

Usage:
  fetch_row.py --key TC-012        (also "tc12", "M-05", "c6")
  fetch_row.py --key "Login wrong password"
  fetch_row.py --row 25            (the row number shown in the sheet)
  fetch_row.py --count             (data rows and the last used row, for appending)
  fetch_row.py --key M-05 --csv /path/to/export.csv
"""
import argparse
import csv
import glob
import json
import os
import re
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config as cfgmod  # noqa: E402

MAX_AGE_SECONDS = 600
KEY_COLUMNS = ["ID", "Test Case", "Source YAML", "Maestro file"]


def newest_download():
    files = glob.glob(os.path.expanduser("~/Downloads/data*.csv"))
    files = [f for f in files if time.time() - os.path.getmtime(f) < MAX_AGE_SECONDS]
    if not files:
        sys.exit("No ~/Downloads/data*.csv from the last 10 minutes. Open the tab's gviz CSV URL "
                 "in Chrome first (references/sheet.md → Fetch).")
    return max(files, key=os.path.getmtime)


def stash(path):
    # Keeps Downloads clean and stops a later run from reading a stale export.
    out_dir = os.path.join(tempfile.gettempdir(), "maestro-scenario")
    os.makedirs(out_dir, exist_ok=True)
    target = os.path.join(out_dir, f"sheet-{int(time.time())}.csv")
    shutil.move(path, target)
    return target


def rows_from_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    if not rows:
        sys.exit(f"{path} is empty")
    return rows[0], rows[1:]


def rows_from_xlsx(path, tab, header_row):
    try:
        import openpyxl
    except ImportError:
        sys.exit("openpyxl is needed for local mode: python3 -m pip install --user openpyxl")
    ws = openpyxl.load_workbook(path, data_only=True)[tab]
    header = [str(c.value or "") for c in ws[header_row]]
    data = []
    for r in ws.iter_rows(min_row=header_row + 1, values_only=True):
        data.append(["" if v is None else str(v) for v in r])
    while data and not any(c.strip() for c in data[-1]):
        data.pop()
    return header, data


def parse_id(value):
    m = re.fullmatch(r"\s*([A-Za-z]+)\s*-?\s*(\d+)\s*", value or "")
    return (m.group(1).upper(), int(m.group(2))) if m else None


def main():
    ap = argparse.ArgumentParser()
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--key", help="ID, test name, or YAML / flow file name")
    group.add_argument("--row", type=int, help="row number shown in the sheet")
    group.add_argument("--count", action="store_true")
    ap.add_argument("--csv", help="read this export instead of the newest download")
    args = ap.parse_args()

    cfg = cfgmod.load()
    sheet = cfg.get("sheet", {})
    first_row = sheet.get("first_row") or 15
    header_row = sheet.get("header_row") or first_row - 1

    if args.csv:
        source = args.csv
        header, data = rows_from_csv(source)
    elif sheet.get("mode") == "local":
        source = os.path.join(cfgmod.repo_root(), sheet["local_path"])
        header, data = rows_from_xlsx(source, sheet.get("tab"), header_row)
    else:
        source = stash(newest_download())
        header, data = rows_from_csv(source)

    if "ID" not in header:
        sys.exit(f"No 'ID' column in the header {header}. Is sheet.header_row ({header_row}) right?")

    if args.count:
        used = [i for i, r in enumerate(data) if any(c.strip() for c in r)]
        last = first_row + used[-1] if used else first_row - 1
        print(json.dumps({"data_rows": len(used), "last_row": last, "next_row": last + 1, "source": source}))
        return

    if args.row is not None:
        i = args.row - first_row
        if not 0 <= i < len(data):
            sys.exit(f"Row {args.row} is outside the data rows ({first_row}–{first_row + len(data) - 1})")
        matches = [(i, dict(zip(header, data[i])))]
    else:
        wanted_id = parse_id(args.key)
        needle = args.key.strip().lower()
        exact, partial = [], []
        for i, cells in enumerate(data):
            record = dict(zip(header, cells))
            if wanted_id and parse_id(record.get("ID", "")) == wanted_id:
                exact.append((i, record))
                continue
            values = [record.get(c, "").strip().lower() for c in KEY_COLUMNS if c in record]
            values += [os.path.basename(v) for v in values if "/" in v]
            if needle in values or needle + ".yaml" in values:
                exact.append((i, record))
            elif not wanted_id and any(needle in v for v in values if v):
                partial.append((i, record))
        matches = exact or partial
        if not matches:
            sys.exit(f"No row matches '{args.key}'. Source kept at {source}")

    i, record = matches[0]
    print(json.dumps({
        "mode": "csv" if args.csv else sheet.get("mode", "google"),
        "sheet_row": first_row + i,
        "row": record,
        "other_matches": [{"sheet_row": first_row + j, "ID": r.get("ID", ""), "Test Case": r.get("Test Case", "")}
                          for j, r in matches[1:]],
        "source": source,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
