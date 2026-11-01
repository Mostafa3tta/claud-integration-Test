#!/usr/bin/env bash
# Run one Maestro flow with debug output and print a short summary.
# Usage: run_flow.sh <flow.yaml> [device-id]
# Without a device id, uses the only connected Android device / booted iOS
# simulator for the platforms in the project config.
# Exit code: 0 when the flow passed, 1 when it failed, 2 on usage errors.
set -uo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
flow="${1:-}"
if [[ -z "$flow" || ! -f "$flow" ]]; then
  echo "usage: run_flow.sh <flow.yaml> [device-id]" >&2
  exit 2
fi

device="${2:-}"
if [[ -z "$device" ]]; then
  platforms=$(python3 "$here/config.py" get project.platforms 2>/dev/null || echo '["android","ios"]')
  devices=""
  if [[ "$platforms" == *android* ]] && command -v adb >/dev/null; then
    devices+=$(adb devices | awk 'NR>1 && $2=="device" {print $1}')$'\n'
  fi
  if [[ "$platforms" == *ios* ]] && command -v xcrun >/dev/null; then
    devices+=$(xcrun simctl list devices booted | sed -nE 's/.*\(([0-9A-F-]{36})\) \(Booted\).*/\1/p')$'\n'
  fi
  devices=$(printf '%s' "$devices" | grep -v '^$' || true)
  count=$(printf '%s\n' "$devices" | grep -c . || true)
  if [[ "$count" -ne 1 ]]; then
    echo "Expected exactly one connected device for $platforms, found $count. Pass the device id:" >&2
    printf '%s\n' "$devices" >&2
    exit 2
  fi
  device="$devices"
fi

name=$(basename "$flow" .yaml)
slug=$(printf '%s' "$name" | tr -c 'A-Za-z0-9_-' '_')
out="${TMPDIR:-/tmp}/maestro-scenario/runs/${slug}-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$out"

echo "Running $flow on $device"
echo "Debug output: $out"
maestro --device "$device" test "$flow" \
  --debug-output "$out" --flatten-debug-output \
  --format junit --output "$out/report.xml" > "$out/console.txt" 2>&1
status=$?

python3 "$here/summarize_run.py" "$out" "$status"
[[ $status -eq 0 ]] && exit 0 || exit 1
