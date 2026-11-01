#!/usr/bin/env python3
"""Summarize the project's existing Maestro flows in one line each.

Used during setup to tell which imported test cases are already covered,
without reading every flow in full. Each line: path, the flow's header
comments, the ids it touches, the texts it asserts, and how many live
assertions it has.

With --unused-ids, also lists test-ID strings defined in the given constants
file that no flow uses: the starting point for finding untested screens.

Usage:
  list_flows.py [flows-dir] [--unused-ids lib/test_ids.dart]
"""
import argparse
import os
import re

# IDs nearly every flow touches (launch / onboarding) say nothing about coverage.
COMMON = set()
ASSERT = re.compile(r"^\s*-\s*assert(Visible|NotVisible|True)\b|^\s*-?\s*extendedWaitUntil\b", re.M)


def summarize(path, root):
    with open(path, encoding="utf-8", errors="replace") as f:
        text = f.read()
    if not re.search(r"^appId:", text, re.M):
        return None
    comments = [l.strip("# ").strip()[:90] for l in text.splitlines() if l.startswith("#")][:1]
    ids = []
    for v in re.findall(r"\bid:\s*\"?([^\"\n]+?)\"?\s*$", text, re.M):
        if v not in ids:
            ids.append(v)
    texts = []
    for v in re.findall(r"assertVisible:\s*\"?([^\"\n{][^\"\n]*)\"?\s*$|text:\s*\"([^\"]+)\"", text, re.M):
        v = next((x for x in v if x), "")
        if v and v not in texts:
            texts.append(v)
    links = re.findall(r"openLink:\s*(\S+)", text)
    parts = [os.path.relpath(path, root)]
    if comments:
        parts.append("about: " + " / ".join(comments))
    if links:
        parts.append("links: " + ", ".join(links[:2]))
    if ids:
        parts.append("ids: " + ", ".join(i for i in ids if i not in COMMON)[:160])
    if texts:
        parts.append("texts: " + ", ".join(t[:30] for t in texts[:4]))
    parts.append(f"asserts: {len(ASSERT.findall(text))}")
    return " | ".join(parts), text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("flows_dir", nargs="?", default="maestro")
    ap.add_argument("--unused-ids")
    args = ap.parse_args()

    root = os.getcwd()
    # First pass: IDs used by more than half the flows are noise in the summary.
    counts, total = {}, 0
    for dirpath, _, files in os.walk(args.flows_dir):
        for name in files:
            if name.endswith((".yaml", ".yml")):
                with open(os.path.join(dirpath, name), encoding="utf-8", errors="replace") as f:
                    found = set(re.findall(r"\bid:\s*\"?([^\"\n]+?)\"?\s*$", f.read(), re.M))
                total += 1
                for i in found:
                    counts[i] = counts.get(i, 0) + 1
    COMMON.update(i for i, c in counts.items() if c > total / 2)
    corpus = []
    count = 0
    for dirpath, _, files in os.walk(args.flows_dir):
        for name in sorted(files):
            if not name.endswith((".yaml", ".yml")):
                continue
            result = summarize(os.path.join(dirpath, name), root)
            if result:
                line, text = result
                print(line)
                corpus.append(text)
                count += 1
    print(f"\n{count} flows")

    if args.unused_ids:
        with open(args.unused_ids, encoding="utf-8", errors="replace") as f:
            src = f.read()
        defined = sorted(set(re.findall(r"['\"]([a-z][a-z0-9_]{3,})['\"]", src)))
        all_flows = "\n".join(corpus)
        unused = [i for i in defined if i not in all_flows]
        print(f"\nTest IDs never used by a flow ({len(unused)} of {len(defined)}):")
        print(", ".join(unused))


if __name__ == "__main__":
    main()
