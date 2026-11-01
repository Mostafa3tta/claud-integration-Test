#!/usr/bin/env python3
"""Read and update the project's maestro-scenario config.

The skill folder is the same in every project; everything project-specific
(app id, build commands, the tracking sheet, ID prefixes) lives in
<repo>/.claude/maestro-scenario.json, which this module finds and edits.

Usage:
  config.py path                      print the config path (exit 1 if missing)
  config.py show                      print the whole config
  config.py get sheet.tab             print one value (JSON for objects)
  config.py set sheet.gid '"0"'       set one value (the value is JSON)
  config.py next-id TC                reserve the next ID for a prefix, print it
"""
import json
import os
import subprocess
import sys

CONFIG_NAME = os.path.join(".claude", "maestro-scenario.json")


def repo_root(start=None):
    start = start or os.getcwd()
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=start, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            return out
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    path = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(path, ".claude")):
            return path
        parent = os.path.dirname(path)
        if parent == path:
            return os.path.abspath(start)
        path = parent


def config_path(root=None):
    return os.path.join(root or repo_root(), CONFIG_NAME)


def load(required=True):
    path = config_path()
    if not os.path.exists(path):
        if required:
            sys.exit(
                f"No config at {path}. Run the skill's setup first "
                "(references/setup.md)."
            )
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    path = config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def get(cfg, dotted, default=None):
    node = cfg
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            return default
        node = node[part]
    return node


def set_value(cfg, dotted, value):
    parts = dotted.split(".")
    node = cfg
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def format_id(prefix, number, digits):
    return f"{prefix}-{number:0{digits}d}"


def reserve_id(cfg, prefix):
    ids = cfg.setdefault("ids", {})
    entry = ids.setdefault(prefix, {"meaning": "", "next": 1, "digits": 3})
    value = format_id(prefix, entry["next"], entry.get("digits", 3))
    entry["next"] += 1
    return value


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cmd = sys.argv[1]
    if cmd == "path":
        path = config_path()
        print(path)
        sys.exit(0 if os.path.exists(path) else 1)
    cfg = load()
    if cmd == "show":
        print(json.dumps(cfg, indent=2, ensure_ascii=False))
    elif cmd == "get":
        value = get(cfg, sys.argv[2])
        if value is None:
            sys.exit(f"{sys.argv[2]} is not set")
        print(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))
    elif cmd == "set":
        set_value(cfg, sys.argv[2], json.loads(sys.argv[3]))
        print(save(cfg))
    elif cmd == "next-id":
        value = reserve_id(cfg, sys.argv[2])
        save(cfg)
        print(value)
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
