# Design System

## Direction

A native libadwaita settings surface with iOS-like clarity: a stable sidebar, grouped settings rows, plain language, and immediate state feedback. The app follows the active GTK light or dark preference and system accent.

Physical scene: one person adjusts a laptop late in the evening, moving quickly between a bright desk and a dark room without wanting to read configuration syntax.

## Design Dials

- Design variance: 4. Familiar structure with a slightly asymmetric summary area.
- Motion intensity: 2. Only standard native state transitions and feedback.
- Visual density: 6. Compact daily controls with comfortable targets.

## Color

Strategy: restrained. Runtime colors come from libadwaita semantic tokens and the active HyDE/GTK theme. The fallback design palette is documented in OKLCH for non-GTK surfaces:

```css
:root {
  --bg: oklch(1 0 0);
  --surface: oklch(0.965 0 0);
  --ink: oklch(0.18 0.01 110);
  --muted: oklch(0.48 0.012 110);
  --primary: oklch(0.65 0.10 110);
  --accent: oklch(0.42 0.12 255);
}
```

Semantic success, warning, and error colors use libadwaita defaults. Color is never the sole indication of state.

## Typography

Use the GTK system UI font throughout. Titles use native title styles. Numbers and durations use tabular figures where available. No display typeface.

## Shape and Spacing

Use libadwaita's native 12px group radius and 6px control radius. Buttons may use the platform's rounded button treatment. Base spacing follows an 8px rhythm with 12px and 18px optical adjustments where native components require them.

## Components

- NavigationSplitView for the app shell.
- PreferencesGroup and ActionRow for settings.
- SpinRow and ComboRow for constrained values.
- SwitchRow for reversible on/off choices.
- Banner for errors or incomplete runtime support.
- Toast for successful apply and transient failures.

## Interaction

Settings remain draft values until Apply is pressed. Live brightness changes are the exception and update immediately. Applying idle settings creates a timestamped backup before replacing the managed file. Screen-time collection has a visible master switch and an explicit erase action.

## Responsive Behavior

The sidebar collapses into navigation on narrow windows. Content remains a single readable column with a maximum width. The app supports keyboard-only operation and never depends on hover.
