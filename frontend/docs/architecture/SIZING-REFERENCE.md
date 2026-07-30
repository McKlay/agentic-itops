# UI Sizing & Teams Responsiveness Reference

> **Last updated:** 2026-05-01  
> **Applies to:** Frontend SPA — browser + Microsoft Teams Personal Tab (iframe)

---

## 1. Teams Iframe Constraints

A Microsoft Teams Personal Tab renders a web app inside an `<iframe>`. The available viewport is **not** the full browser window — Teams chrome (header bar, side rail, chat pane) consumes significant space.

| Context | Typical iframe width | Typical iframe height |
|---|---|---|
| Teams Desktop — full tab | 900–1280 px | 600–800 px |
| Teams Desktop — side panel open | 600–900 px | 600–800 px |
| Teams Desktop — pop-out window | 400–1400 px (user-resizable) | 400–900 px |
| Teams Web (browser) | Same as desktop, minus browser chrome | Same |
| Teams Mobile (iOS/Android) | 320–428 px | ~600 px |
| Standalone browser (no Teams) | 1280–1920 px | 720–1080 px |

### Zoom Levels

Teams desktop supports 80%–200% zoom. At 150% zoom on a 1280px monitor, the effective viewport is ~853px — triggering our `≤860px` single-column breakpoint.

**Design target:** Ensure usability at **960px effective width** (covers Teams desktop at 100% zoom with side panel open).

---

## 2. Typography — Fluent UI Type Ramp

All font sizes are sourced from the [Fluent UI type ramp](https://developer.microsoft.com/en-us/fluentui#/styles/web/typography). Teams uses **Segoe UI** as its primary typeface.

| Token | Size | Line Height | Usage in this app |
|---|---|---|---|
| `size10` | 10px | 14px | Footer labels ("Powered by…"), disclaimers |
| `size12` | 12px | 16px | Metadata, timestamps, feed card agent names, metric tile labels |
| `size14` | 14px | 20px | **Body text default** — chat messages, input fields, nav items, descriptions |
| `size16` | 16px | 22px | Workspace header title, section headers |
| `size18` | 18px | 24px | Metric tile values, page section titles |
| `size20` | 20px | 28px | HomePage hero heading |
| `size24` | 24px | 32px | *Reserved — not used in current UI* |
| `size28` | 28px | 36px | *Reserved — page titles if full-screen* |

### Font Weights

| Weight | Value | Usage |
|---|---|---|
| Regular | 400 | Body text, descriptions, input placeholders |
| Semibold | 600 | Nav labels, card titles, section headers, metric values |
| Bold | 700 | Hero heading, brand name, key metric numbers |

---

## 3. Icon Sizing

All icons are custom SVG components in `src/components/shared/Icons.tsx`. They use a `viewBox="0 0 24 24"` base with stroke-based rendering for crisp display at all scales.

| Context | Icon Size | Rationale |
|---|---|---|
| Sidebar nav items | 16px | Matches 14px text with comfortable optical weight |
| Quick-action card icons | 18px | ~1.3× body text — visible but not dominant |
| Composer toolbar buttons | 13–14px | Inside 28px hit targets — subtly functional |
| Session action buttons (rename/delete) | 12px | Minimal chrome, appears on hover only |
| Activity feed empty state | 24px | Decorative illustration placeholder |
| Theme/role toggle inline icons | 12px | Compact footer region |

### Icon Design Principles

- **Stroke-only** line art (strokeWidth 1.75) — no fills for consistency
- Monochrome — inherits `currentColor` from parent text color
- All icons include `aria-hidden="true"` — not exposed to screen readers
- `shrink-0` on icon containers to prevent flex collapse in tight layouts

---

## 4. Spacing — 4px Grid

Following Fluent UI's 4px base grid:

| Token | Value | Usage |
|---|---|---|
| `gap-0.5` | 2px | Tight vertical stacks (metric tile label gap) |
| `gap-1` | 4px | Icon-to-text in compact controls |
| `gap-2` | 8px | Card internal padding, button groups |
| `gap-2.5` | 10px | Icon-to-label in nav items |
| `gap-3` | 12px | Grid gaps, section spacing |
| `px-3` / `py-2.5` | 12px / 10px | Metric tile padding |
| `px-4` / `py-3` | 16px / 12px | Quick-action card padding |
| `px-5` / `py-4` | 20px / 16px | Sidebar brand block, feed header |
| `px-6` / `py-3` | 24px / 12px | Composer wrapper |

---

## 5. Layout Dimensions

### Three-Panel Grid

| Panel | Width | Rationale |
|---|---|---|
| Sidebar | 240px | Fits nav labels + session list; leaves room for content at 960px |
| Workspace | fluid `1fr` | Expands to fill; content max-width capped at 760px for readability |
| Activity Feed | 280px | 3 metric tiles + feed cards fit comfortably |

### Responsive Breakpoints

| Breakpoint | Behavior | Teams Scenario |
|---|---|---|
| `≤ 1200px` | Chart grids collapse to 1 column | — |
| `≤ 1180px` | Activity Feed hides; Sidebar shrinks to 220px | Teams with side panel open |
| `≤ 860px` | Sidebar hides; single-column layout | Teams at 150%+ zoom |

---

## 6. Hit Target Minimums

Per WCAG 2.1 and Fluent UI guidance:

| Element | Minimum Size | Current Size |
|---|---|---|
| Nav buttons | 44×32px | `w-full py-1.5` = ~240×28px ✓ |
| Session row (clickable) | 44×32px | `w-full py-2` = ~220×32px ✓ |
| Composer icon buttons | 28×28px | `w-7 h-7` = 28×28px ✓ |
| Rating emoji buttons | 28×28px | `w-7 h-7` = 28×28px ✓ |
| Quick-action cards | 44×44px+ | ~240×80px ✓ |
| Theme toggle buttons | 44×24px | `flex-1 py-1.5` = ~110×24px ✓ |

---

## 7. Border Radius — Fluent UI Alignment

| Token | Value | Usage |
|---|---|---|
| `--radius-sm` | 4px | Small pills, tags |
| `--radius-md` | 8px | Buttons, input fields, nav items |
| `--radius-lg` | 12px | Cards, panels, modals |
| `--radius-xl` | 16px | Hero logo, quick-action cards |
| `--radius-full` | 9999px | Avatars, circular badges |

---

## 8. Teams-Specific Considerations

1. **No hover on mobile Teams:** Touch targets must be large enough for tap (44px min). Quick-action cards already exceed this.

2. **Theme synchronization:** Teams exposes three themes (light, dark, high-contrast). The app supports light/dark via `data-theme` attribute. High-contrast support can be added by reading `microsoftTeams.getContext()` and mapping to CSS custom properties.

3. **Safe area:** Teams iframe includes a small top/bottom safe area. The app's `h-screen` grid fills the iframe completely — no additional padding needed.

4. **Zoom resilience:** All sizing uses `px` values (matching Fluent UI) rather than `rem` to avoid compounding zoom effects from Teams' own zoom controls. The CSS `font-size: 14px` on `<body>` sets the baseline.

5. **Content max-width:** Chat conversation and composer are capped at 760px via `max-w-[760px] mx-auto` — this prevents text lines from becoming unreadably wide on large monitors while keeping optimal line length (60–80 characters at 14px).
