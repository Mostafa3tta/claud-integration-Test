#!/usr/bin/env python3
"""Condense a Maestro debug-output folder into what's needed to fix a flow.

Prints the result, the failing command with its error, the last steps that
completed, and the failure screenshots, so the raw commands JSON and log
(often thousands of lines) never have to be read in full.

Usage: summarize_run.py <debug-output-dir> <maestro-exit-code>
"""
import glob
import json
import os
import re
import sys


def describe(command):
    """One line per command: its type plus the selector or value it used."""
    if not isinstance(command, dict) or not command:
        return str(command)
    kind, body = next(iter(command.items()))
    if not isinstance(body, dict):
        return f"{kind}: {body}"
    parts = []
    selector = body.get("selector") or {}
    if isinstance(selector, dict):
        for k, v in selector.items():
            if k != "optional" and v not in (None, False, "", [], {}):
                parts.append(f"{k}={v}")
    for k in ("text", "condition", "element", "script", "link", "appId", "direction"):
        v = body.get(k)
        if v not in (None, "", {}, []):
            parts.append(f"{k}={json.dumps(v, ensure_ascii=False)[:160]}")
    if body.get("optional"):
        parts.append("optional")
    return f"{kind}({', '.join(parts)})" if parts else kind


def error_text(metadata):
    err = metadata.get("error")
    if isinstance(err, dict):
        return err.get("message") or json.dumps(err, ensure_ascii=False)[:400]
    return str(err) if err else ""


def main():
    out, exit_code = sys.argv[1], int(sys.argv[2])
    console = os.path.join(out, "console.txt")
    console_text = open(console, encoding="utf-8", errors="replace").read() if os.path.exists(console) else ""

    result = re.findall(r"\[(Passed|Failed)\][^\n]*", console_text)
    print("RESULT:", "PASSED" if exit_code == 0 else "FAILED", "|", result[-1] if result else "")

    commands_files = glob.glob(os.path.join(out, "commands-*.json"))
    if not commands_files:
        print("No commands JSON. Maestro probably failed before running the flow:")
        print("\n".join(console_text.strip().splitlines()[-25:]))
        return

    entries = []
    for path in commands_files:
        with open(path, encoding="utf-8") as f:
            entries.extend(json.load(f))
    entries.sort(key=lambda e: e.get("metadata", {}).get("sequenceNumber", 0))

    statuses = [e.get("metadata", {}).get("status") for e in entries]
    print(f"Steps: {len(entries)} | " + ", ".join(
        f"{s}={statuses.count(s)}" for s in sorted(set(filter(None, statuses)))))

    failed = [e for e in entries if e.get("metadata", {}).get("status") == "FAILED"]
    if failed:
        idx = entries.index(failed[0])
        meta = failed[0]["metadata"]
        print(f"\nFAILED at step #{meta.get('sequenceNumber')}: {describe(failed[0].get('command'))}")
        msg = error_text(meta)
        if msg:
            print("Error:", msg)
        print("\nLast completed steps before it:")
        for e in [e for e in entries[:idx] if e.get("metadata", {}).get("status") == "COMPLETED"][-5:]:
            print(f"  #{e['metadata'].get('sequenceNumber')} {describe(e.get('command'))}")
    elif exit_code != 0:
        print("\nNo step marked FAILED; end of the console output:")
        print("\n".join(console_text.strip().splitlines()[-25:]))

    shots = sorted(glob.glob(os.path.join(out, "*.png")))
    if shots:
        print("\nScreenshots (read the ❌ one first):")
        for s in shots[-6:]:
            print(" ", s)
    print("\nFolder:", out)


if __name__ == "__main__":
    main()
