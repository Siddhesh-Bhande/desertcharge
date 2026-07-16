# DesertCharge design tokens (v1)

Canonical palette and type, extracted from the approved screen mockup (v1). The
implementation derives every color and type decision from this file. Solid colors
only in the UI chrome (no gradients). The one gradient-like element allowed is the
desert-score data scale, because that is a data encoding, not decoration.

## Color primitives

| Token          | Hex       | Notes                                            |
|----------------|-----------|--------------------------------------------------|
| basalt-900     | `#12151A` | Dark map base and app chrome                     |
| basalt-800     | `#1A1D22` | Raised panels, bottom sheet, cards               |
| basalt-700     | `#22262C` | Subtle raised (keyboard keys, insets)            |
| bone-100       | `#E9E3D6` | Light surface, and primary text on dark          |
| ironwood-900   | `#241F1A` | Ink: text on light, and text on the brass accent |
| clay-600       | `#6B6152` | Muted labels on the bone surface                 |
| brass-400      | `#C9A467` | PRIMARY accent: interactive, CTA, focus, selected|
| rust-600       | `#B4552F` | Warm emphasis and warnings, used sparingly       |
| rust-700       | `#8A3E20` | Links (hover moves to brass-400)                 |
| teal-600       | `#2E6E75` | Charger map pins, served/secondary marker        |
| cyan-400       | `#34C7D4` | Atmospheric only, very low opacity (loaders)     |

Text-on-dark uses `bone-100` at opacity steps: 1.0 primary, 0.75 secondary, 0.6 and
0.5 tertiary, 0.45 faint. Hairlines use `bone-100` at 0.12 to 0.28.

## Semantic roles

| Role                    | Token        |
|-------------------------|--------------|
| surface / app base      | basalt-900   |
| surface / raised        | basalt-800   |
| surface / light         | bone-100     |
| text / on-dark          | bone-100     |
| text / on-light         | ironwood-900 |
| text / muted-on-light   | clay-600     |
| accent / primary        | brass-400    |
| accent / on-primary     | ironwood-900 |
| accent / warning        | rust-600     |
| link / default          | rust-700     |
| link / hover            | brass-400    |
| focus ring              | brass-400    |
| map / charger pin       | teal-600     |
| map / selected location | brass-400    |
| map / best-site marker  | bone-100     |

## Desert-score scale (data encoding)

Sequential, cool served to hot desert. Always shown with the number and a word
label, never color alone (accessibility).

| Band   | Label    | Hex       |
|--------|----------|-----------|
| 0-20   | served   | `#1B9E8A` |
| 21-40  | good     | `#7FB069` |
| 41-60  | moderate | `#E6B23A` |
| 61-80  | poor     | `#D57A33` |
| 81-100 | desert   | `#B23A24` |

Note to reconcile in build: the mockup gauge fills a score of 78 with `rust-600`
(#B4552F) and labels it "desert," while this scale puts 61-80 at "poor" (#D57A33).
Pick one and use it for both the gauge and the heat layer so they agree. Default:
follow this 5-band scale for both. Revisit if the punchier rust reads better on the
gauge.

## Typography

| Role    | Family          | Setting                                   |
|---------|-----------------|-------------------------------------------|
| Display | Archivo         | Expanded (font-stretch 125%), weight 700-800; headings and score numerals |
| Body    | Public Sans     | weight 400-800                            |
| Mono    | IBM Plex Mono   | weight 400-600; readouts and labels, uppercase, letter-spacing 0.1 to 0.2em |

All three are open-source (Google Fonts). Public Sans ties to US public-data
typography (USWDS), which suits the Census-backed subject.

## Radius, elevation, focus

| Token              | Value                              |
|--------------------|------------------------------------|
| radius / sheet     | 20px (top corners on bottom sheets)|
| radius / card      | 14px                               |
| radius / control   | 12px (list rows, buttons)          |
| radius / pill      | 999px (chips, segmented control)   |
| radius / device    | 28px (mockup frame only)           |
| elevation / sheet  | `0 24px 60px rgba(36,31,26,.22)`   |
| focus ring         | `0 0 0 1.5px #C9A467`              |

Registration ticks: small L-shaped corner marks, `1px` in `bone-100` at 0.4 opacity,
on raised panels. This is the signature "field instrument" detail; keep it subtle.

## Motion

Subtle only. Loader spin at 1.4s linear. Sheet transitions around 220ms with a light
spring. All motion is disabled under `prefers-reduced-motion: reduce`.

## Guardrails (from rules.md)

No gradients in chrome. No purple-to-indigo. No neon glow. No emoji as icons or
headers. No centered oversized hero. No identical card grids. No lorem ipsum. No em
dashes in any copy. Real Southwest place and network names only.
