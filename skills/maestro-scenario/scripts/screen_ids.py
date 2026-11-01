#!/usr/bin/env python3
"""List what Maestro can target on the device's current screen.

`maestro hierarchy` prints the whole view tree (system bars included), which
is long and mostly noise. This keeps only the app's elements: resource-id
(Flutter Semantics identifier), text / accessibility text, and whether the
element is clickable, in screen order.

Usage: screen_ids.py [device-id] [--all]
  --all  also list elements that have neither an id nor a text
"""
import re
import subprocess
import sys

SYSTEM_ID = re.compile(r"^(com\.android\.|android:id/)")


def attrs(raw):
    out = {}
    for part in raw.split("; "):
        if "=" in part:
            k, v = part.split("=", 1)
            out.setdefault(k.strip(), v.strip())
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    show_all = "--all" in sys.argv
    cmd = ["maestro"] + (["--device", args[0]] if args else []) + ["hierarchy", "--compact"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(proc.stderr.strip() or "maestro hierarchy failed")

    seen = set()
    for line in proc.stdout.splitlines()[1:]:
        m = re.match(r'^\d+,\d+,"(.*)",\d*$', line)
        if not m:
            continue
        a = attrs(m.group(1))
        rid = a.get("resource-id", "")
        if SYSTEM_ID.match(rid):
            continue
        text = a.get("text") or a.get("accessibilityText") or a.get("hintText") or ""
        if rid and text == rid:
            text = ""  # Flutter mirrors the identifier into the label
        if not (rid or text or show_all):
            continue
        key = (rid, text, a.get("bounds"))
        if key in seen:
            continue
        seen.add(key)
        flags = " [tap]" if a.get("clickable") == "true" else ""
        flags += " [scroll]" if a.get("scrollable") == "true" else ""
        if a.get("checked") == "true":
            flags += " [checked]"
        label = f"id={rid}" if rid else ""
        if text:
            label += (" " if label else "") + f'text="{text[:80]}"'
        print(f"{label or '(no id/text)'}{flags}  {a.get('bounds', '')}")


if __name__ == "__main__":
    main()
