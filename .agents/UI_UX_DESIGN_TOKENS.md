# 🎨 Wedding Planner Engine: UI/UX Design System & Editorial Frontend Specification

> Dokumen spesifikasi desain frontend, token CSS variabel, skala modular tipografi, pustaka komponen, pola interaksi asinkronus (HTMX & Alpine.js), dan layout responsif untuk antarmuka web platform Wedding Planner SaaS.

---

## 1. Design Philosophy: Bold Editorial SaaS

Antarmuka menggabungkan efisiensi sistem modular SaaS dengan sentuhan tipografi majalah editorial high-end (*Linear meets High-Fashion Wedding Editorial*).

### 1.1. Core Principles
1. **High Visual Contrast:** Blok gelap kontras tinggi (*Deep Forest Obsidian*) dipadukan dengan kanvas terang hangat (*Warm Alabaster*).
2. **Intentional Typographic Tension:** Ketegasan sans-serif geometris modern bertabrakan secara harmonis dengan 1 kata kunci serif miring (*Instrument Serif Italic*).
3. **Semantic Hierarchy:** Tiga aksen warna tegas tanpa gradasi ambigu:
   * **Vintage Gold:** Metrik finansial, anggaran, dan kepemilikan dana bersama.
   * **Forest Sage:** Tamu undangan, kalkulasi katering, dan indikator aman/sukses.
   * **Terracotta Clay:** Tenggat waktu, pembayaran jatuh tempo, dan peringatan kritis.
4. **Micro-Border & Zero-Friction Surfaces:** Menghindari drop-shadow berat; mengandalkan garis pembatas 1px (*greige micro-borders*) dan kontras latar permukaan (*bento surface*).

---

## 2. Complete Design Tokens (CSS Custom Properties)

```css
:root {
  /* ==========================================================================
     CANVAS & SURFACE PALETTE
     ========================================================================== */
  --wp-bg-canvas: #FAF8F5;              /* Warm Alabaster (Global Background) */
  --wp-bg-surface: #FFFFFF;             /* Pure White (Card & Bento Container) */
  --wp-bg-surface-subtle: #F4F0E8;      /* Warm Tint (Input Background & Table Head) */
  --wp-bg-surface-muted: #EFEAE1;       /* Neutral Container Background */

  /* ==========================================================================
     DARK HERO & CONTAINER BLOCKS
     ========================================================================== */
  --wp-dark-hero: #0F1A15;              /* Deep Forest Midnight */
  --wp-dark-hero-surface: #182821;      /* Elevated Dark Card Surface */
  --wp-dark-border: #23382F;            /* Deep Green Accent Border */

  /* ==========================================================================
     SEMANTIC COLOR TOKENS
     ========================================================================== */
  /* Gold / Champagne (Finance, Wealth, Summary KPI) */
  --wp-gold-main: #C8A261;              /* Rich Champagne Gold */
  --wp-gold-dark: #8C6621;              /* Deep Gold Text */
  --wp-gold-soft: #F9F4EB;              /* Soft Gold Surface Tint */
  --wp-gold-border: #E2CCA0;            /* Gold Accent Border */

  /* Sage / Emerald (Guests, Food, Stability, Success) */
  --wp-sage-main: #386641;              /* Forest Sage */
  --wp-sage-dark: #122817;              /* Deep Sage Text */
  --wp-sage-soft: #EAF4EC;              /* Soft Sage Surface Tint */
  --wp-sage-border: #B8DCBF;            /* Sage Accent Border */

  /* Terracotta / Amber (Alerts, Overdue, Critical Deadlines) */
  --wp-terracotta-main: #D97757;        /* Earthy Terracotta */
  --wp-terracotta-dark: #4A2218;        /* Deep Terracotta Text */
  --wp-terracotta-soft: #FDF2EE;        /* Soft Terracotta Surface Tint */
  --wp-terracotta-border: #F8C3B3;      /* Terracotta Accent Border */

  /* ==========================================================================
     TYPOGRAPHY & NEUTRALS
     ========================================================================== */
  --wp-text-main: #141716;              /* Obsidian Charcoal (Primary Headings & Values) */
  --wp-text-secondary: #5F6662;         /* Muted Slate (Subtitles & Labels) */
  --wp-text-muted: #8A928D;             /* Subtle Gray (Metadata & Timestamps) */
  --wp-text-inverse: #FFFFFF;           /* White (Text on Dark Containers) */
  
  --wp-border-light: #E7E2D8;           /* Standard Card Border */
  --wp-border-hover: #C8A261;           /* Interactive Hover Border */

  /* ==========================================================================
     RADII & ELEVATIONS
     ========================================================================== */
  --wp-radius-xs: 4px;                  /* Mini Badges & Tags */
  --wp-radius-sm: 8px;                  /* Buttons & Form Inputs */
  --wp-radius-md: 14px;                 /* Bento Cards & Table Containers */
  --wp-radius-lg: 20px;                 /* Hero Banners & Modals */
  --wp-radius-pill: 500px;              /* Circular Badges & Pills */

  --wp-shadow-card: 0 2px 6px rgba(20, 23, 22, 0.03);
  --wp-shadow-elevated: 0 4px 14px rgba(20, 23, 22, 0.06);
  --wp-shadow-hero: 0 12px 32px -8px rgba(15, 26, 21, 0.25);
  --wp-shadow-dropdown: 0 10px 25px -5px rgba(20, 23, 22, 0.1);

  /* ==========================================================================
     TRANSITIONS & ANIMATIONS
     ========================================================================== */
  --wp-transition-fast: 0.15s ease;
  --wp-transition-normal: 0.25s ease;
}