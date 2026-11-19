---
name: Rangkai
description: Calm, high-precision operational wedding planning workspace combining pure Zinc neutral shadcn/ui (radix-nova) content surfaces with Rangkai's signature Deep Imperial Forest sidebar and Imperial Emerald accents.
colors:
  canvas-light: "#f5f5f7"
  card-light: "#ffffff"
  sidebar-light: "#0b1e17"
  muted-light: "#f1f1f4"
  foreground-light: "#09090b"
  muted-foreground-light: "#6b6b76"
  border-light: "#dfdfe4"
  primary-light: "#126e51"
  primary-hover-light: "#0e5a42"
  primary-foreground-light: "#ffffff"
  canvas-dark: "#0a0a0d"
  card-dark: "#16161b"
  popover-dark: "#1c1c22"
  sidebar-dark: "#111115"
  muted-dark: "#1e1e24"
  foreground-dark: "#fafafa"
  muted-foreground-dark: "#a1a1aa"
  border-dark: "#2a2a32"
  primary-dark: "#22a076"
  primary-hover-dark: "#2cb487"
  primary-foreground-dark: "#051b14"
  destructive-light: "#dc2626"
  destructive-dark: "#f87171"
  warning-light: "#b45309"
  warning-dark: "#fbbf24"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1.5rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  kpi:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "1.55rem"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.5
  label:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif"
    fontSize: "0.8125rem"
    fontWeight: 500
    lineHeight: 1.3
  mono:
    fontFamily: "JetBrains Mono, ui-monospace, SFMono-Regular, Menlo, monospace"
    fontSize: "0.82rem"
    fontWeight: 600
    lineHeight: 1.4
rounded:
  xs: "4px"
  sm: "6px"
  md: "8px"
  lg: "10px"
  xl: "12px"
  full: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "14px"
  lg: "20px"
  xl: "24px"
components:
  button-primary:
    backgroundColor: "{colors.primary-light}"
    textColor: "{colors.primary-foreground-light}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 11px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover-light}"
    textColor: "{colors.primary-foreground-light}"
  button-outline:
    backgroundColor: "{colors.card-light}"
    textColor: "{colors.foreground-light}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 11px"
  card-light:
    backgroundColor: "{colors.card-light}"
    textColor: "{colors.foreground-light}"
    rounded: "{rounded.xl}"
    padding: "16px"
  card-dark:
    backgroundColor: "{colors.card-dark}"
    textColor: "{colors.foreground-dark}"
    rounded: "{rounded.xl}"
    padding: "16px"
  input-light:
    backgroundColor: "{colors.card-light}"
    textColor: "{colors.foreground-light}"
    rounded: "{rounded.md}"
    height: "32px"
    padding: "0 10px"
---

## Overview

Rangkai (`rangkai.click`) is a multi-tenant Indonesian wedding planning workspace built on Django 5.1, HTMX, Alpine.js, and pure Vanilla CSS (no Node/Tailwind build step). Its visual system follows **shadcn/ui (`radix-nova`)** operational precision: crisp Zinc tonal layering for effortless figure-ground separation in both Light and Dark modes, paired with **Imperial Emerald** reserved strictly as Rangkai's primary brand accent.

Source of truth files:
- Tokens: `static/css/design-tokens.css`
- shadcn/ui Vanilla CSS primitives & shell: `static/css/shadcn-ui.css`
- Local component reference catalog: `.agents/references/shadcn/INDEX.md`

## Colors

Rangkai uses a **Restrained Neutral + Single Brand Accent** strategy with deliberate tonal stepping so cards never melt into the canvas:

### Light Mode (Zinc Tonal Stepping)
- **Canvas (`--background`):** `#f5f5f7` — cool off-white workspace ground so pure white cards separate immediately without heavy shadows.
- **Card & Chrome (`--card`, `--sidebar`):** `#ffffff` with `#dfdfe4` hairline borders.
- **Muted / Track (`--muted`, `--secondary`):** `#f1f1f4` / `#f4f4f5` for segmented tab tracks, table headers, and inline drawers inside white cards.
- **Primary Brand Accent (`--primary`):** `#126e51` (Imperial Emerald; hover `#0e5a42`, foreground `#ffffff`). Used exclusively for primary CTAs, active navigation indicators, focus rings, readiness progress bars, and key positive KPI highlights.

### Dark Mode (Zinc Tonal Elevation)
- **Canvas (`--background`):** `#0a0a0d` — deepest workspace ground.
- **Sidebar (`--sidebar`):** `#101014` with `#24242b` border.
- **Card (`--card`):** `#16161b` — clear tonal lift above the canvas with `#2a2a32` border and subtle `inset 0 1px 0 rgba(255, 255, 255, 0.04)` top-edge definition.
- **Popover / Floating (`--popover`):** `#1c1c22`.
- **Primary Brand Accent (`--primary`):** `#22a076` (hover `#2cb487`, foreground `#051b14`).

### Semantic Status Colors
- **Success / Lunas / Hadir:** `#126e51` (light) / `#34d399` (dark) on 10–15% tint.
- **Warning / Jatuh Tempo / Prioritas:** `#b45309` (light) / `#fbbf24` (dark) on 11–14% tint.
- **Destructive / Overdue / Over-Allocated:** `#dc2626` (light) / `#f87171` (dark) on 10–16% tint.

## Typography

- **UI Sans (`--font-sans`):** `Inter` (loaded via Google Fonts, weights 400–700). All headings, navigation, labels, controls, and body copy use upright `Inter` with tight display tracking (`-0.025em` on page titles, `-0.03em` on KPI figures).
- **Mono & Tabular Data (`--font-mono`, `.tabular-nums`):** `JetBrains Mono` and `font-variant-numeric: tabular-nums` are required on all Rupiah (`Rp`) figures, percentages, dates, and 8-character workspace invite codes.
- **Hierarchy:** Page title `1.5rem` (600), KPI value `1.4–1.55rem` (650), Card title `0.9375rem` (600), Body `0.875rem` (400), Secondary/Table cells `0.8125–0.84rem`, Badges & captions `0.72–0.78rem`.

## Layout

- **App Shell (`templates/base.html`):** Collapsible desktop sidebar (`16rem` expanded ↔ `3.25rem` icon rail, keyboard shortcut `Ctrl+B` / `Cmd+B`) paired with a sticky `52px` top breadcrumb header (`[data-slot="site-header"]`) inside `<main class="main-content">` so HTMX navigation (`hx-boost`) automatically updates breadcrumbs and header actions.
- **Content Container:** `.ui-page-container` / `.workspace-canvas` capped at `1280px` (`padding: 24px 24px 44px` desktop; `16px 14px 32px` mobile) with `20px` vertical stack rhythm.
- **Responsive Grids:**
  - KPI strip: 4 columns desktop (`repeat(4, minmax(0, 1fr))`), auto-adapts to 3 columns when exactly 3 KPIs exist (e.g. `Crew` dashboard or Checklist), 2 columns tablet, 1 column mobile.
  - Split operational workspaces: 2 equal-height columns desktop (`align-items: stretch`), stacking to 1 column below `960px`.
- **Mobile (`≤ 768px`):** Sidebar transforms into a slide-in `18rem` Sheet drawer; a 5-slot Bottom Navigation bar anchors the 4 primary destinations (`Ringkasan`, `Anggaran`/`Logistik`, `Tugas`, `Tamu`) plus the `Menu` Sheet trigger, auto-hiding when a virtual keyboard is open (`body.kbd-open`).

## Elevation & Depth

Rangkai relies primarily on **tonal surface stepping + 1px hairline borders**, not heavy drop shadows or glassmorphism:
- **Flat/Base:** Canvas (`--background`).
- **Raised Card (`--shadow-xs`):** Light `0 1px 2px rgba(9, 9, 11, 0.04)`; Dark `0 1px 2px rgba(0, 0, 0, 0.40), inset 0 1px 0 rgba(255, 255, 255, 0.04)`.
- **Floating Overlays (`--shadow-lg`):** Dropdowns, tooltips, Sonner toasts, and right inspector Sheets.
- **Backdrop Blur:** Used sparingly only on the sticky top header (`8px`) and modal/sheet scrims (`2px`).

## Shapes

- **Controls (`Button`, `Input`, `SidebarItem`, `TabsList`):** `8px` (`--radius-md`); compact `sm` controls use `6px` (`--radius-sm`).
- **Containers (`Card`, `Alert`, `Dialog`):** `12px` (`--radius-xl`).
- **Nested Cards / Phase & Category Tabs:** `10px` (`--radius-lg`).
- **Badges, Switches, Progress Tracks:** `9999px` (`--radius-full`).
- **Checkboxes:** `5px` crisp square.

## Components

All primitives use semantic `data-slot` / `data-variant` / `data-size` attributes in `static/css/shadcn-ui.css` (aligned with `.agents/references/shadcn/components/`):
- **Button (`[data-slot="button"]`):** `default` (Emerald), `outline`, `secondary`, `ghost`, `destructive`, `link`; heights `xs` (24px), `sm` (28px), `default` (32px), `lg` (36px), `icon` / `icon-sm`. Focus ring: `0 0 0 3px var(--ring-soft)`.
- **Card (`[data-slot="card"]`):** Supports `data-size="sm"` for KPI cards and `data-flush="true"` when hosting full-bleed lists or tables below a bordered header.
- **Badge (`[data-slot="badge"]`):** `default`, `secondary`, `outline`, `success`, `warning`, `destructive`.
- **Tabs / Segmented Filters (`.filter-segmented`):** Muted track with elevated white/card active pill.
- **Table (`[data-slot="table"]` / `.sheet-table`):** `36px` muted header, `10px 12px` cell padding, subtle row hover, right-aligned tabular numerals for currency.
- **Empty State (`[data-slot="empty"]`):** Centered bordered `38–40px` muted icon tile, concise title, and actionable muted description.
- **Toast (`#wp-toast-container`):** Bottom-right Sonner-style floating stack (above bottom nav on mobile); errors persist until dismissed.

## Do's and Don'ts

- **Do** preserve tonal separation between `--background` (canvas) and `--card` in both Light (`#f5f5f7` vs `#ffffff`) and Dark (`#0a0a0d` vs `#16161b`) modes.
- **Do** use `tabular-nums` and `font-mono` for Rupiah (`Rp`), percentages, and invite codes.
- **Do** keep `Imperial Emerald` restrained for primary actions, active states, progress, and positive status.
- **Don't** put white cards on pure `#ffffff` canvas or near-black cards on `#09090b` canvas without tonal contrast.
- **Don't** reintroduce legacy glassmorphism shadows, decorative eyebrow kickers above headings, italic serif display headings inside operational screens, or Node/Tailwind build dependencies.
- **Don't** break HTMX `.main-content` swap targets, Alpine.js state, role isolation (`is_crew`), or Driver.js `#guide-*` tour IDs.
