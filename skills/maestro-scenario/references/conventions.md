# Writing flows that stay honest

General Maestro rules learned from real suites. The project's own habits win: before writing, open one or two passing flows in `flows.dir` that touch the same screens and copy their navigation, waits, logins and subflows.

## File skeleton

```yaml
appId: <app.<platform>.app_id>
---
# TC-012 — Login with wrong password
# Source: <sheet title> / <tab> (rows move; find the case by ID)
# Expected: error message shown; user stays on Login

<flows.start_snippet>

# …steps…
```

- The start snippet usually launches with `clearState: true`, so every flow starts as a fresh install and flows don't depend on each other. Launch once.
- First-launch screens (onboarding, permissions, cookie banners) belong in the start snippet with `optional: true`, so the flow also survives builds that don't show them.
- If `flows.subflows_dir` exists, reuse its subflows (`- runFlow: subflows/login.yaml`) instead of copying their steps. Add a subflow only when a second flow needs the same steps.

## Selectors

- **Prefer `id:`.** How the app's widgets expose IDs to Maestro depends on the framework: see [test-ids.md](test-ids.md). Look the ID up in code (`test_ids.constants_file` if there is one) instead of guessing.
- **Suffixes are added at runtime:** an index (`_0`), a record id (`_4713448`) or a state (`_on` / `_off`). Check how the widget builds the ID, and use a regex when the suffix depends on data: `id: "product_card_.*"`.
- **Text only when there's no ID,** as a regex that survives copy changes: `text: ".*Results"`, `"From \\d+ km"`. If the app is localized, texts change with the device language, which is one more reason to prefer IDs.
- **Avoid `point:` coordinates and multi-line text selectors.** They break on another screen size or with other data. When unavoidable (an element with no node of its own, such as a dialog barrier or video controls), leave a comment saying why.

## Waiting and scrolling

- **Network content:** `extendedWaitUntil` with a timeout, 10–30 s for screens, longer for web views or slow back-ends.
- **Transitions and sheets:** `waitForAnimationToEnd`.
- **Never a fixed sleep to "fix" timing.** It slows the suite down and still flakes.
- **Scrolling:** `scrollUntilVisible` with `direction:`, plus `centerElement: true` for long forms.
- **Keyboard:** close it after typing, before tapping something it may cover. `hideKeyboard` can press Back when no keyboard is open (closing the screen) on some apps, and `pressKey: Enter` is the safer choice there.

## Assertions

- **Every Expected Result item** gets an assertion that fails if that item breaks. `extendedWaitUntil` counts too: it fails when the element never shows.
- **Counts:** read them, convert them, compare with real operators:

  ```yaml
  - copyTextFrom:
      id: results_count
  - evalScript: ${output.before = Number(maestro.copiedText.replace(/\D/g, ''))}
  # …change the filter…
  - copyTextFrom:
      id: results_count
  - evalScript: ${output.after = Number(maestro.copiedText.replace(/\D/g, ''))}
  - assertTrue: ${output.after <= output.before}
  ```

  Inside `assertTrue`, write `==`, `<` or `<=`, never a single `=`. `${a = b}` assigns, is truthy, and can never fail; it is the most common silent bug in inherited Maestro suites.
- **No commented-out assertions and no `optional: true` on assertions:** a flow without live assertions always passes and proves nothing.
- **`assertNotVisible` alone is weak:** it passes when the screen didn't load at all. Pair it with an `assertVisible` that proves you're on the right screen. To prove an error comes from an action, assert it's not visible before the action and visible after.
- **Don't assert test data that will change** (names, prices, exact counts). Assert relationships (fewer, equal to before) or formats (regex).

## Accounts and data

- Log in the way `flows.accounts` says: usually a login subflow. Don't invent accounts, and don't paste credentials into chat, the sheet or notes.
- Sign-up cases need a fresh address each run: `${"test_user_" + new Date().getTime() + "@example.com"}`.
- Payments: only the test cards and sandbox accounts the project's flows already use.
- Cases that need special data (an item with a video, an order in a given state) should reach it through a search or a setup subflow that reliably finds such data, not a hard-coded record id, unless the case is about that record.

## Device-level steps

If Maestro rejects a command as unknown, the run fails at once with that message. Then run the fallback from the shell between two flows.

| Need | Maestro | Fallback |
|---|---|---|
| Back (Android) | `- back` | |
| Background, then resume | `- pressKey: Home` … `- launchApp: {stopApp: false}` | |
| Kill and relaunch | `- stopApp` then `- launchApp` (no clearState) | `adb shell am force-stop <app_id>` / `xcrun simctl terminate <device> <app_id>` |
| No network | `- setAirplaneMode: enabled` … `disabled` | `adb shell svc wifi disable; adb shell svc data disable` |
| Rotate | `- setOrientation: LANDSCAPE_LEFT` … `PORTRAIT` | `adb shell settings put system user_rotation 1` |
| Permission dialogs | `launchApp: {permissions: {all: allow}}` or tap the system button by text | |
| What Maestro can't assert (video playing, sound) | `- takeScreenshot: <name>` at two moments | Compare the screenshots with the Read tool and say in the Note that this was checked visually |

Put airplane mode, rotation and similar device settings back at the end of the flow, or the next flow starts broken.

Some things don't work on emulators, such as hardware video decoding, push from FCM/APNs and biometrics. When a case needs one, say so in the Note and keep the flow in a separate folder (e.g. `<flows.dir>/real-device/`) so the emulator suite stays green.

## Naming and placement

- New case: `<flows.dir>/<ID>-<short-kebab-title>.yaml` (or `flows.naming`).
- Ported from an older flow: keep its file name unless `flows.naming` says otherwise.
- Don't edit other flows to make yours pass. If a shared problem shows up (a changed ID used everywhere), report it.
