#!/usr/bin/env python3
"""Dump a test-cases document as plain text, whatever format it came in.

Testers and clients send test cases as spreadsheets, Word files, CSV,
Markdown or plain text. This prints the content in a form that can be read
and normalized into one row per test case, without extra dependencies
(openpyxl is used for .xlsx when installed).

Supported: .xlsx/.xlsm, .csv/.tsv, .docx, .md/.txt/.json.
For .pdf and images, read the file with the Read tool instead.

Usage:
  read_source.py <file> [--sheet NAME] [--max-rows N]
"""
import argparse
import csv
import json
import os
import re
import sys
import zipfile
from xml.etree import ElementTree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def cell_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def import_openpyxl():
    # `python3 -I` (used for untrusted files) hides the user's site-packages,
    # where openpyxl is usually installed; add that one directory back.
    try:
        import openpyxl
        return openpyxl
    except ImportError:
        import site
        user_site = site.getusersitepackages()
        if os.path.isdir(user_site) and user_site not in sys.path:
            sys.path.append(user_site)
        import openpyxl
        return openpyxl


def dump_xlsx(path, only_sheet, max_rows):
    try:
        openpyxl = import_openpyxl()
    except ImportError:
        sys.exit("openpyxl is not installed: run `python3 -m pip install --user openpyxl`, "
                 "or export the file as CSV and pass that instead.")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    for ws in wb.worksheets:
        if only_sheet and ws.title != only_sheet:
            continue
        print(f"\n## Sheet: {ws.title}")
        shown = 0
        for i, row in enumerate(ws.iter_rows(values_only=True), 1):
            cells = [cell_text(v) for v in row]
            while cells and not cells[-1]:
                cells.pop()
            if not any(cells):
                continue
            print(f"{i}\t" + "\t".join(cells))
            shown += 1
            if max_rows and shown >= max_rows:
                print(f"… stopped after {max_rows} rows (use --max-rows 0 for all)")
                break


def dump_csv(path, max_rows):
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as f:
        sample = f.read(4096)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel_tab if path.endswith(".tsv") else csv.excel
        for i, row in enumerate(csv.reader(f, dialect), 1):
            if any(c.strip() for c in row):
                print(f"{i}\t" + "\t".join(cell_text(c) for c in row))
            if max_rows and i >= max_rows:
                print(f"… stopped after {max_rows} rows")
                break


def dump_docx(path):
    with zipfile.ZipFile(path) as z:
        root = ElementTree.fromstring(z.read("word/document.xml"))
    body = root.find(f"{W}body")

    def text_of(node):
        return "".join(t.text or "" for t in node.iter(f"{W}t"))

    for block in body:
        if block.tag == f"{W}p":
            style = block.find(f"{W}pPr/{W}pStyle")
            line = text_of(block).strip()
            if not line:
                continue
            numbered = block.find(f"{W}pPr/{W}numPr") is not None
            name = style.get(f"{W}val") if style is not None else ""
            if name.lower().startswith("heading"):
                level = re.sub(r"\D", "", name) or "2"
                print("#" * min(int(level) + 1, 6), line)
            else:
                print(("- " if numbered else "") + line)
        elif block.tag == f"{W}tbl":
            print("\n[table]")
            for row in block.iter(f"{W}tr"):
                cells = [re.sub(r"\s+", " ", text_of(c)).strip() for c in row.iter(f"{W}tc")]
                print(" | ".join(cells))
            print("[/table]\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--sheet")
    ap.add_argument("--max-rows", type=int, default=0)
    args = ap.parse_args()
    path = args.file
    if not os.path.exists(path):
        sys.exit(f"{path} not found")
    ext = os.path.splitext(path)[1].lower()
    print(f"# Source: {os.path.basename(path)}")
    if ext in (".xlsx", ".xlsm"):
        dump_xlsx(path, args.sheet, args.max_rows)
    elif ext in (".csv", ".tsv"):
        dump_csv(path, args.max_rows)
    elif ext == ".docx":
        dump_docx(path)
    elif ext in (".md", ".txt", ".json", ".yaml", ".yml"):
        with open(path, encoding="utf-8", errors="replace") as f:
            print(f.read())
    elif ext in (".xls", ".doc", ".pages", ".numbers", ".odt", ".ods"):
        sys.exit(f"{ext} is an older or non-Office format: ask for it as .xlsx, .docx or .csv "
                 "(File → Save As / Export), or as a Google Docs/Sheets link.")
    else:
        sys.exit(f"{ext}: read it with the Read tool (PDF, images) or ask for .xlsx/.docx/.csv.")


if __name__ == "__main__":
    main()
