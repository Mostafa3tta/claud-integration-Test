#!/usr/bin/env python3
"""Put HTML (with a plain-text fallback) on the system clipboard, so it can be
pasted into Google Sheets with formatting and formulas intact.

Large tables are too big to pass through the browser tools, so the clipboard
is filled from the shell and the sheet only receives a Cmd/Ctrl+V.

macOS: Swift (NSPasteboard), falling back to AppleScript.
Linux: wl-copy or xclip.
Windows: not supported; upload the .xlsx to Google Drive instead.

Usage: set_clipboard.py <file.html> [<file.tsv>]
"""
import os
import shutil
import subprocess
import sys
import tempfile

SWIFT = """
import AppKit
let a = CommandLine.arguments
let html = try! String(contentsOfFile: a[1], encoding: .utf8)
let txt = a.count > 2 ? try! String(contentsOfFile: a[2], encoding: .utf8) : html
let pb = NSPasteboard.general
pb.clearContents()
pb.setString(html, forType: .html)
pb.setString(txt, forType: .string)
"""


def mac(html_path, txt_path):
    if shutil.which("swift"):
        with tempfile.NamedTemporaryFile("w", suffix=".swift", delete=False) as f:
            f.write(SWIFT)
        try:
            args = ["swift", f.name, html_path] + ([txt_path] if txt_path else [])
            if subprocess.run(args, capture_output=True, text=True, timeout=180).returncode == 0:
                return "swift"
        finally:
            os.unlink(f.name)
    with open(html_path, "rb") as f:
        hexdata = f.read().hex()
    script = f'set the clipboard to «data HTML{hexdata}»'
    if subprocess.run(["osascript", "-e", script], capture_output=True).returncode == 0:
        return "osascript"
    return None


def linux(html_path):
    with open(html_path, "rb") as f:
        data = f.read()
    for cmd in (["wl-copy", "--type", "text/html"], ["xclip", "-selection", "clipboard", "-t", "text/html", "-i"]):
        if shutil.which(cmd[0]):
            if subprocess.run(cmd, input=data).returncode == 0:
                return cmd[0]
    return None


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    html_path = sys.argv[1]
    txt_path = sys.argv[2] if len(sys.argv) > 2 else None
    if sys.platform == "darwin":
        how = mac(html_path, txt_path)
    elif sys.platform.startswith("linux"):
        how = linux(html_path)
    else:
        how = None
    if not how:
        sys.exit("Could not set the clipboard here. Use the .xlsx instead: upload it to Google Drive "
                 "and open it with Google Sheets (references/setup.md, step 5 fallback).")
    print(f"clipboard set via {how} ({os.path.getsize(html_path)} bytes of HTML)")


if __name__ == "__main__":
    main()
