# How each framework exposes test IDs to Maestro

Maestro's `id:` matches the platform's accessibility identifier: `resource-id` on Android and `accessibilityIdentifier` on iOS. Each framework gets there differently, which is what `test_ids.mechanism` in the config records. When a step fails because an element has no ID, this is the change to propose (after asking, see SKILL.md step 6). Copy the codebase's existing pattern (`test_ids.pattern`) over these generic examples.

## Flutter: `flutter-semantics`

```dart
Semantics(
  identifier: TestIds.loginSubmitButton,   // 'login_submit_button'
  label: TestIds.loginSubmitButton,
  child: ElevatedButton(...),
)
```

- `identifier` (Flutter 3.19+) becomes the Android `resource-id` and the iOS `accessibilityIdentifier`.
- Many codebases also set `label` to the same string, because some Maestro versions match on it. Copy what the project does.
- Keep the strings in one constants file (`test_ids.constants_file`) and add new ones next to their neighbors with the same naming.
- **Lists:** add the index or record id at runtime, `'${TestIds.productCard}_$index'`, and match it in flows with a regex.
- **Elements Flutter merges** (a tile whose children have no Semantics of their own): add `Semantics` on the child you need, or `excludeSemantics`/`container: true` so it gets its own node.

## React Native: `rn-testid`

```tsx
<Pressable testID="login_submit_button" accessibilityLabel="Sign in">…</Pressable>
```

- `testID` is the `resource-id` on Android (React Native 0.64+, no extra setup) and the `accessibilityIdentifier` on iOS.
- Custom components must forward `testID` to a native view, or nothing shows up.

## Native Android (Views): `android-resource-id`

- The view's `android:id="@+id/login_submit_button"` is already the `resource-id`.
- Maestro matches the id name. Use a regex if the full form includes the package (`com.example:id/login_submit_button`).

## Jetpack Compose: `compose-testtag`

```kotlin
Modifier.testTag("login_submit_button")
// once, on the root:
Modifier.semantics { testTagsAsResourceId = true }
```

Without `testTagsAsResourceId = true` the tags aren't visible to Maestro.

## Native iOS (UIKit / SwiftUI): `ios-accessibility-id`

```swift
button.accessibilityIdentifier = "login_submit_button"          // UIKit
Button("Sign in") { … }.accessibilityIdentifier("login_submit_button")  // SwiftUI
```

## Checking what Maestro sees

With the app on the screen in question:

```bash
python3 <skill-dir>/scripts/screen_ids.py [device]
```

If the new ID isn't in the list after rebuilding and reinstalling, it didn't reach the platform layer. Usually a wrapper component dropped it, or Flutter merged the node into its parent.
