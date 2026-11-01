#!/usr/bin/env python3
"""Detect what setup needs to know about a project, so it can propose
answers instead of asking for them.

Prints JSON: framework, Android application ids and flavors, iOS bundle ids,
Flutter entry points, existing Maestro flow folders and the app ids they use,
the start steps most flows share, likely test-ID constant files, connected
devices and installed tools. Every value is a guess for the user to confirm.

Usage: detect_project.py [repo-root]
"""
import collections
import glob
import json
import os
import re
import shutil
import subprocess
import sys

SKIP_DIRS = {".git", "build", "node_modules", "Pods", ".dart_tool", ".gradle",
             ".idea", "DerivedData", ".symlinks", "ephemeral"}


def walk(root, exts, limit=20000):
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            if name.endswith(exts):
                count += 1
                if count > limit:
                    return
                yield os.path.join(dirpath, name)


def read(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def run(cmd):
    if not shutil.which(cmd[0]):
        return None
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None


def framework(root):
    if os.path.exists(os.path.join(root, "pubspec.yaml")):
        return "flutter"
    pkg = os.path.join(root, "package.json")
    if os.path.exists(pkg):
        text = read(pkg)
        if '"expo"' in text:
            return "react-native-expo"
        if '"react-native"' in text:
            return "react-native"
    if glob.glob(os.path.join(root, "**", "build.gradle*"), recursive=True):
        if glob.glob(os.path.join(root, "*.xcodeproj")) or glob.glob(os.path.join(root, "ios", "*.xcodeproj")):
            return "native-android-and-ios"
        return "native-android"
    if glob.glob(os.path.join(root, "**", "*.xcodeproj"), recursive=True):
        return "native-ios"
    return "unknown"


def android(root):
    out = {"application_ids": [], "flavors": {}}
    for gradle in glob.glob(os.path.join(root, "**", "build.gradle*"), recursive=True):
        if any(part in SKIP_DIRS for part in gradle.split(os.sep)):
            continue
        text = read(gradle)
        out["application_ids"] += re.findall(r'applicationId\s*=?\s*"([^"]+)"', text)
        for name, body in re.findall(r"(?:create\(\"|\b)(\w+)\"?\)?\s*\{([^{}]*applicationIdSuffix[^{}]*)\}", text):
            m = re.search(r'applicationIdSuffix\s*=?\s*"([^"]+)"', body)
            if m:
                out["flavors"][name] = m.group(1)
    out["application_ids"] = sorted(set(out["application_ids"]))
    out["candidates"] = sorted({a + s for a in out["application_ids"] for s in [""] + list(out["flavors"].values())})
    return out


def ios(root):
    ids = set()
    for proj in glob.glob(os.path.join(root, "**", "project.pbxproj"), recursive=True):
        if "Pods" in proj:
            continue
        ids.update(re.findall(r"PRODUCT_BUNDLE_IDENTIFIER = \"?([^;\"]+)\"?;", read(proj)))
    app_ids = sorted(i for i in ids if not re.search(r"Tests|Extension|Service|Widget|Intent|\$\(", i))
    return {"bundle_ids": app_ids, "all": sorted(ids)}


def flutter_entries(root):
    return sorted(os.path.relpath(p, root) for p in glob.glob(os.path.join(root, "lib", "main*.dart")))


def flows(root):
    folders = collections.Counter()
    app_ids = collections.Counter()
    starts = collections.Counter()
    for path in walk(root, (".yaml", ".yml")):
        text = read(path)
        m = re.search(r"^appId:\s*(\S+)", text, re.M)
        if not m:
            continue
        rel = os.path.relpath(path, root)
        folders[rel.split(os.sep)[0] if os.sep in rel else "."] += 1
        app_ids[m.group(1)] += 1
        body = text.split("---", 1)[-1].strip().splitlines()
        steps, block = [], []
        for line in body:
            if line.startswith("#") or not line.strip():
                continue
            if line.startswith("- ") and block:
                steps.append("\n".join(block))
                block = []
            block.append(line.rstrip())
            if len(steps) >= 6:
                break
        if block:
            steps.append("\n".join(block))
        for k in range(1, len(steps) + 1):
            starts["\n".join(steps[:k])] += 1
    total = sum(folders.values())
    # The longest opening that most flows share; a lower bar only if none does.
    common = ""
    for share in (0.4, 0.25):
        for snippet, count in sorted(starts.items(), key=lambda kv: -len(kv[0])):
            if total and count >= max(3, total * share):
                common = snippet
                break
        if common:
            break
    return {"folders": dict(folders), "app_ids": dict(app_ids), "total": total, "common_start": common}


def test_id_files(root, fw):
    patterns = {
        "flutter": r"identifier:\s*",
        "react-native": r"testID=",
        "react-native-expo": r"testID=",
        "native-android": r"testTag\(|contentDescription",
        "native-ios": r"accessibilityIdentifier",
    }
    usage = re.compile(patterns.get(fw, r"identifier:|testID=|testTag\(|accessibilityIdentifier"))
    const = re.compile(r"static const String \w+\s*=\s*['\"][a-z0-9_]+['\"]|export const \w+\s*=\s*['\"][a-z0-9_-]+['\"]|const val \w+\s*=\s*\"[a-z0-9_]+\"")
    users, consts = 0, []
    exts = (".dart", ".ts", ".tsx", ".js", ".jsx", ".kt", ".java", ".swift")
    for path in walk(root, exts):
        text = read(path)
        users += len(usage.findall(text))
        n = len(const.findall(text))
        name = os.path.basename(path).lower()
        if n >= 15 and re.search(r"id|key|test|semantic", name):
            consts.append((n, os.path.relpath(path, root)))
    return {"usages": users, "constant_files": [p for _, p in sorted(consts, reverse=True)[:5]]}


def devices():
    out = {"android": [], "ios": []}
    adb = run(["adb", "devices"])
    if adb:
        out["android"] = [l.split()[0] for l in adb.splitlines()[1:] if l.strip().endswith("device")]
    simctl = run(["xcrun", "simctl", "list", "devices", "booted", "-j"])
    if simctl:
        try:
            for runtime in json.loads(simctl).get("devices", {}).values():
                out["ios"] += [f"{d['udid']} ({d['name']})" for d in runtime if d.get("state") == "Booted"]
        except ValueError:
            pass
    return out


def tools():
    return {
        "maestro": (run(["maestro", "--version"]) or "").splitlines()[-1:] or None,
        "adb": bool(shutil.which("adb")),
        "xcrun": bool(shutil.which("xcrun")),
        "flutter": bool(shutil.which("flutter")),
        "python_openpyxl": _has_openpyxl(),
    }


def _has_openpyxl():
    try:
        import openpyxl  # noqa: F401
        return True
    except ImportError:
        return False


def main():
    root = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    fw = framework(root)
    print(json.dumps({
        "root": root,
        "framework": fw,
        "android": android(root),
        "ios": ios(root),
        "flutter_entry_points": flutter_entries(root) if fw == "flutter" else [],
        "flows": flows(root),
        "test_ids": test_id_files(root, fw),
        "devices": devices(),
        "tools": tools(),
    }, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
