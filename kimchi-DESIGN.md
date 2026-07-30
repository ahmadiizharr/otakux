# Design System Inspired by Kimchi

## 1. Visual Theme & Atmosphere

Kimchi's design system embodies a bold, developer-centric aesthetic that thrives on dark backgrounds with vibrant accent colors. The visual language is energetic yet professional, combining stark contrast with luminous highlights to create urgency and draw attention to critical actions. The typography is sharp and geometric, utilizing modern sans-serif faces to communicate technical sophistication. The overall mood is one of innovation and efficiency—a platform designed for developers who demand speed, clarity, and visual feedback. Subtle motion and carefully calibrated shadows reinforce hierarchy without overwhelming the interface, while the generous use of orange as a primary accent creates immediate visual association with the Kimchi brand and conveys action and momentum.

**Key Characteristics**
- Dark mode-first design with near-black backgrounds
- Vibrant, saturated accent colors (especially orange) for CTAs and highlights
- High contrast between text and backgrounds for accessibility
- Geometric, modern typography with strong weight differentiation
- Minimal ornamental elements; content-focused layout
- Monospace fonts for code contexts and technical elements
- Bold color applications for status and semantic meaning
- Clean card-based layouts with subtle borders and elevation

## 2. Color Palette & Roles

### Primary
- **Brand Orange** (`#FF521D`): Primary CTA buttons, hero highlights, accent text, and dominant brand identity. Used extensively across interactive elements and key messaging.

### Accent Colors
- **Success Green** (`#4ED996`): Positive confirmations, successful operations, completion states, and prosperity indicators.
- **Sky Blue** (`#7BD3F7`): Information callouts, secondary interactive states, and digital/connected messaging.
- **Lime Green** (`#C8E96A`): Highlight accents and supplementary visual signaling for code or data elements.
- **Electric Lime** (`#E2FF7A`): High-contrast highlights, attention-grabbing secondary accents, and neon-style emphasis.
- **Teal** (`#6DB7A7`): Tertiary accent for calming information areas and balanced visual weight distribution.
- **Cream** (`#E8C97C`): Warm accent for gentle highlighting and softer emphasis contexts.

### Interactive
- **Orange Hover** (`#FF521D` at 85% opacity): Reduced-saturation state for interactive hover feedback on orange elements.
- **Orange Focus** (`#FF521D` at 70% opacity): Subtle focus ring and keyboard navigation indication.

### Neutral Scale
- **Pure White** (`#FFFFFF`): Primary text on dark backgrounds, high-contrast elements, and maximum readability.
- **Light Gray** (`#F5F5F5`): Secondary text, placeholder text, and subtle UI elements on light or mid-tone backgrounds.
- **Dark Charcoal** (`#1E1E20`): Secondary text, subtle UI elements, and low-emphasis content on light backgrounds.
- **Medium Gray** (`#A6A6A6`): Disabled states, muted text, and tertiary information hierarchy.
- **Zinc Gray** (`#A1A1AA`): Caption text, meta-information, and secondary interface labels.
- **Deep Charcoal** (`#161618`): Tertiary dark backgrounds and strong contrast layers.
- **Dark Slate** (`#242426`): Secondary dark backgrounds and card containers with mild elevation.
- **Almost Black** (`#18181A`): Deepest dark background color for maximum contrast contexts.

### Surface & Borders
- **Dark Surface Default** (`#1E1E20`): Primary surface for cards, modals, and contained UI areas.
- **Dark Surface Secondary** (`#242426`): Secondary surface layers for nested content and slightly elevated contexts.
- **Border Subtle** (`rgba(255, 255, 255, 0.1)`): Soft borders between dark surfaces and subtle dividers.
- **Border Muted** (`rgba(255, 255, 255, 0.45)`): Medium-emphasis borders for input fields and interactive elements.
- **Overlay Dark** (`rgba(0, 0, 0, 0.5)`): Semi-transparent overlays for modals and dropdown backgrounds.

### Semantic / Status
- **Warning Amber** (`#FFB84D`): Warning alerts and caution-level notifications.
- **Warning Gold** (`#FEBC2E`): Secondary warning emphasis and medium-priority alerts.
- **Warning Amber Alt** (`#FBBF24`): Tertiary warning signaling and low-priority cautions.
- **Success Bright** (`#28C840`): Positive completion, success confirmations, and approval states.

## 3. Typography Rules

### Font Family
**Primary:** Geist (sans-serif; fallback: `-apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", sans-serif`)  
**Secondary:** Inter (sans-serif; fallback: `ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`)  
**Monospace:** Geist Mono (monospace; fallback: `"Courier New", monospace`)

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|---|---|
| Display / H1 | Geist | 68px | 700 | 69.36px | 0px | Hero headlines; maximum visual impact |
| Heading / H2 | Geist | 56px | 700 | 60.48px | 0px | Section headings; primary content breaks |
| Subheading / H3 | Geist | 28px | 600 | 31.36px | 0px | Card titles; feature headlines |
| Small Heading / H4 | Geist | 14px | 600 | 20px | 0px | Minor section labels; sidebar titles |
| Body / Large | Inter | 19px | 400 | 28.5px | 0px | Primary body copy; descriptive text |
| Body / Regular | Inter | 16px | 400 | 27.2px | 0px | Standard UI text; link default |
| Button / Label | Inter | 16px | 500 | 27.2px | 0px | Primary and secondary button text |
| Caption / Small | Inter | 12px | 500 | 20.4px | 0px | UI captions; metadata labels |
| List Item | Inter | 13.5px | 400 | 20.25px | 0px | List content; bullet point text |
| Tab / Navigation | Geist Mono | 11px | 500 | 18.7px | 0px | Tab labels; code-like UI markers |
| Micro / Badge | Geist Mono | 12.5px | 500 | 18.75px | 0px | Badge labels; status badges |

### Principles
- **Contrast First:** Maximize contrast between text and background for dark-mode readability.
- **Weight Hierarchy:** Use weight shifts (400, 500, 600, 700) to establish content priority rather than size alone.
- **Monospace for Technical:** Reserve Geist Mono for code snippets, terminal output, technical labels, and developer-facing interfaces.
- **Line Height Generosity:** Maintain elevated line heights (1.3–1.5) for body text to support longer reading sessions in dark mode.
- **Semantic Sizing:** Avoid arbitrary sizes; every type scale step must serve a clear hierarchy level.

## 4. Component Stylings

### Buttons

**Primary Button**
- Background: `#FF521D`
- Text Color: `#FFFFFF`
- Font: Inter, 16px, 500
- Padding: `12px 24px`
- Border Radius: `10px`
- Border: `none`
- Box Shadow: `#FF521D 0px 6px 20px -6px` (on hover/active states)
- Hover: Background `#E64A18` (darken by 8%)
- Active: Background `#CC401A` (darken by 15%)
- Focus: Outline `2px solid #FF521D` at `4px` offset
- Line Height: 27.2px
- Transition: `background-color 200ms ease`

**Secondary Button**
- Background: `rgba(0, 0, 0, 0)` (transparent)
- Text Color: `#FF521D`
- Font: Inter, 16px, 500
- Padding: `12px 24px`
- Border Radius: `10px`
- Border: `2px solid #FF521D`
- Box Shadow: `none`
- Hover: Background `rgba(255, 82, 29, 0.1)`
- Active: Background `rgba(255, 82, 29, 0.2)`
- Focus: Outline `2px solid #FF521D` at `4px` offset
- Line Height: 27.2px
- Transition: `all 200ms ease`

**Ghost Button (Neutral)**
- Background: `rgba(0, 0, 0, 0)` (transparent)
- Text Color: `rgba(255, 255, 255, 0.45)`
- Font: Inter, 16px, 500
- Padding: `12px 24px`
- Border Radius: `10px`
- Border: `1px solid rgba(255, 255, 255, 0.2)`
- Box Shadow: `none`
- Hover: Text Color `#FFFFFF`, Border `1px solid rgba(255, 255, 255, 0.4)`
- Active: Background `rgba(255, 255, 255, 0.05)`
- Focus: Outline `2px solid rgba(255, 255, 255, 0.6)` at `4px` offset
- Line Height: 27.2px
- Transition: `all 200ms ease`

**Small Icon Button**
- Background: `rgba(0, 0, 0, 0)` (transparent)
- Text Color: `rgba(255, 255, 255, 0.45)`
- Font: Geist Mono, 12.5px, 500
- Padding: `5px`
- Width: `24px`
- Height: `24px`
- Border Radius: `4px`
- Border: `1px solid rgba(255, 255, 255, 0.1)`
- Box Shadow: `none`
- Hover: Background `rgba(255, 255, 255, 0.05)`, Border `1px solid rgba(255, 255, 255, 0.2)`
- Active: Background `rgba(255, 255, 255, 0.1)`
- Line Height: 18.75px
- Transition: `all 150ms ease`

**Tab Button (Navigation)**
- Background: `rgba(0, 0, 0, 0)` (transparent)
- Text Color: `#FF521D`
- Font: Geist Mono, 11px, 500
- Padding: `6px 12px`
- Height: `32px`
- Border Radius: `0px`
- Border: `0px` (bottom border on active only)
- Hover: Text Color `#FF521D`, opacity `0.8`
- Active: Border Bottom `2px solid #FF521D`, Text Color `#FF521D`
- Inactive: Text Color `rgba(255, 255, 255, 0.45)`
- Line Height: 18.7px
- Transition: `all 150ms ease`

### Cards & Containers

**Card Default**
- Background: `#161618`
- Text Color: `#F5F5F5`
- Font: Inter, 16px, 400
- Padding: `28px`
- Border Radius: `12px`
- Border: `1px solid rgba(255, 255, 255, 0.1)`
- Box Shadow: `none`
- Line Height: 27.2px
- Margin Bottom: `24px`

**Card Elevated**
- Background: `#1E1E20`
- Text Color: `#FFFFFF`
- Font: Inter, 16px, 400
- Padding: `32px`
- Border Radius: `12px`
- Border: `1px solid rgba(255, 255, 255, 0.15)`
- Box Shadow: `0px 8px 24px rgba(0, 0, 0, 0.4)`
- Line Height: 27.2px
- Margin Bottom: `32px`

**Card Bordered Accent**
- Background: `#1E1E20`
- Text Color: `#FFFFFF`
- Font: Inter, 16px, 400
- Padding: `28px`
- Border Radius: `12px`
- Border: `2px solid #FF521D`
- Box Shadow: `0px 4px 12px rgba(255, 82, 29, 0.15)`
- Line Height: 27.2px
- Margin Bottom: `24px`

**Code Block Container**
- Background: `#0F0F11`
- Text Color: `#E2FF7A`
- Font: Geist Mono, 12px, 400
- Padding: `16px`
- Border Radius: `4px`
- Border: `1px solid rgba(255, 255, 255, 0.1)`
- Box Shadow: `inset 0px 2px 4px rgba(0, 0, 0, 0.5)`
- Line Height: 18px
- Overflow X: `auto`

### Inputs & Forms

**Text Input Default**
- Background: `#0F0F11`
- Text Color: `#FFFFFF`
- Font: Inter, 16px, 400
- Padding: `12px 16px`
- Height: `44px`
- Border Radius: `8px`
- Border: `1px solid rgba(255, 255, 255, 0.15)`
- Box Shadow: `none`
- Placeholder Color: `rgba(255, 255, 255, 0.35)`
- Focus: Border `1px solid #FF521D`, Box Shadow `0px 0px 0px 3px rgba(255, 82, 29, 0.15)`
- Line Height: 24px
- Transition: `all 200ms ease`

**Text Input Focused**
- Border: `1px solid #FF521D`
- Box Shadow: `0px 0px 0px 3px rgba(255, 82, 29, 0.15)`
- Outline: `none`

**Text Input Error**
- Border: `1px solid #FFB84D`
- Box Shadow: `0px 0px 0px 3px rgba(255, 184, 77, 0.1)`
- Background: `rgba(255, 184, 77, 0.05)`

**Textarea**
- Background: `#0F0F11`
- Text Color: `#FFFFFF`
- Font: Inter, 14px, 400
- Padding: `12px 16px`
- Min Height: `120px`
- Border Radius: `8px`
- Border: `1px solid rgba(255, 255, 255, 0.15)`
- Focus: Border `1px solid #FF521D`, Box Shadow `0px 0px 0px 3px rgba(255, 82, 29, 0.15)`
- Resize: `vertical`
- Line Height: 24px

**Label**
- Font: Inter, 14px, 600
- Color: `#FFFFFF`
- Margin Bottom: `8px`
- Display: `block`

### Navigation

**Navigation Bar**
- Background: `#18181A`
- Text Color: `#F5F5F5`
- Font: Inter, 16px, 400
- Padding: `16px 32px`
- Height: `56px`
- Border: `0px` (bottom border: `1px solid rgba(255, 255, 255, 0.1)`)
- Box Shadow: `0px 4px 12px rgba(0, 0, 0, 0.3)`
- Display: `flex`
- Align Items: `center`
- Justify Content: `space-between`
- Position: `sticky`
- Top: `0`
- Z Index: `1000`
- Line Height: 27.2px

**Navigation Link**
- Color: `#A1A1AA`
- Font: Inter, 14px, 500
- Padding: `8px 16px`
- Border Radius: `6px`
- Text Decoration: `none`
- Hover: Color `#FFFFFF`, Background `rgba(255, 255, 255, 0.05)`
- Active: Color `#FF521D`, Background `rgba(255, 82, 29, 0.1)`
- Transition: `all 150ms ease`

**Logo**
- Width: `auto`
- Height: `32px`
- Display: `flex`
- Align Items: `center`
- Color: `#FFFFFF`

### Badges

**Badge Primary**
- Background: `#FF521D`
- Text Color: `#FFFFFF`
- Font: Geist Mono, 12px, 500
- Padding: `4px 12px`
- Border Radius: `4px`
- Border: `none`
- Display: `inline-block`
- Line Height: 18px

**Badge Secondary**
- Background: `rgba(255, 82, 29, 0.15)`
- Text Color: `#FF521D`
- Font: Geist Mono, 12px, 500
- Padding: `4px 12px`
- Border Radius: `4px`
- Border: `1px solid #FF521D`
- Display: `inline-block`
- Line Height: 18px

**Badge Success**
- Background: `#4ED996`
- Text Color: `#0F0F11`
- Font: Geist Mono, 12px, 500
- Padding: `4px 12px`
- Border Radius: `4px`
- Border: `none`
- Display: `inline-block`
- Line Height: 18px

**Badge Neutral**
- Background: `rgba(255, 255, 255, 0.1)`
- Text Color: `#A1A1AA`
- Font: Geist Mono, 12px, 500
- Padding: `4px 12px`
- Border Radius: `4px`
- Border: `none`
- Display: `inline-block`
- Line Height: 18px

## 5. Layout Principles

### Spacing System

**Base Unit:** `4px`

**Scale:**
- **XS:** `4px` — Tight spacing between inline elements
- **S:** `8px` — Small gaps between components
- **SM:** `12px` — Minor spacing between sections
- **M:** `16px` — Standard padding inside containers
- **ML:** `20px` — Medium spacing between major sections
- **L:** `24px` — Large gaps between sections
- **XL:** `28px` — Extra-large section spacing
- **2XL:** `32px` — Generous section separation
- **3XL:** `36px` — Hero section and page-level spacing
- **4XL:** `40px` — Widest spacing for visual emphasis
- **5XL:** `44px` — Deep padding for prominent containers
- **6XL:** `48px` — Maximum structural spacing

**Context Usage:**
- Horizontal spacing between nav items: `16px`
- Vertical spacing between cards: `24px` to `32px`
- Internal card padding: `28px` to `32px`
- Section margins: `40px` to `48px`
- Hero/header padding: `48px` to `64px` (vertical)

### Grid & Container

**Max Width:** `1224px` (for desktop layouts)  
**Outer Margins:** `32px` on each side at max width  
**Column Strategy:** 12-column grid system at desktop, collapsing to 1 column on mobile  
**Gutter:** `24px` between columns

**Section Patterns:**
- Full-width hero with centered content container
- Side-by-side cards (50/50 split at desktop, stacked on tablet/mobile)
- Three-column feature grid (33/33/33 at desktop, collapsing to single column on mobile)
- Navigation horizontal bar spanning full width with centered max-width container
- Feature comparison table with horizontal scroll on mobile

### Whitespace Philosophy

The design system embraces generous whitespace to reduce cognitive load and allow content to breathe. Dark backgrounds necessitate strategic use of light text and whitespace to maintain accessibility and visual clarity. Section breaks are emphasized through increased vertical spacing (`32px` to `48px`) rather than heavy dividers. Internal component spacing uses consistent multiples of the base unit to create visual rhythm and predictability. Breathing room around CTAs (buttons, links) makes interactive elements more discoverable. Negative space is treated as a design element equal in importance to positive space.

### Border Radius Scale

- **None:** `0px` — Tab bars, full-width elements, code blocks
- **Subtle:** `4px` — Icon buttons, small UI elements, minor components
- **Standard:** `8px` — Form inputs, small cards, secondary containers
- **Prominent:** `10px` — Primary buttons, featured containers
- **Soft:** `12px` — Large cards, modals, major UI sections
- **Generous:** `16px` — Hero sections, large container elements

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat / L0 | No shadow; `0px 0px 0px rgba(0, 0, 0, 0)` | Backgrounds, text, disabled states |
| Raised / L1 | `0px 2px 4px rgba(0, 0, 0, 0.2)` | Standard cards, minor containers |
| Elevated / L2 | `0px 4px 12px rgba(0, 0, 0, 0.3)` | Floating containers, prominent cards |
| High / L3 | `0px 8px 24px rgba(0, 0, 0, 0.4)` | Modals, dropdowns, popovers |
| Maximum / L4 | `0px 16px 48px rgba(0, 0, 0, 0.5)` | Full-screen overlays, top-level modals |
| Accent / Orange Glow | `#FF521D 0px 6px 20px -6px` | Primary buttons (hover/active), accent highlights |

**Shadow Philosophy:** Shadows are used sparingly and with restraint to maintain the clean aesthetic. They rely on opacity and color subtlety rather than blur spread to avoid visual heaviness on dark backgrounds. The orange accent shadow is reserved for high-priority interactive elements (primary buttons and brand-critical CTAs) to draw user attention without overwhelming the interface. Inset shadows (`inset 0px 2px 4px`) are used for code blocks and recessed input fields to suggest depth and containment.

## 7. Do's and Don'ts

### Do
- **Use orange (`#FF521D`) for all primary CTAs** — Consistency reinforces brand identity and user familiarity.
- **Maintain minimum 4.5:1 contrast ratio** for all text on backgrounds, especially in dark mode.
- **Apply generous padding (24px–32px) inside cards** to avoid crowding and improve scannability.
- **Reserve accent colors semantically** — Use green for success, orange for action, amber for warnings, blue for info.
- **Use Geist for headings and Geist Mono for technical labels** — Reinforce information hierarchy and content type.
- **Layer white/light text on dark backgrounds** for optimal readability in dark mode.
- **Include hover and active states on all interactive elements** — Provide clear visual feedback.
- **Use border-radius strategically** — Softer corners on larger components, crisp corners on small utilities.
- **Employ consistent spacing multiples** — Every gap should align to the 4px base unit scale.
- **Test all interactive elements for keyboard navigation** — Focus states must be visible with minimum 2px outline.

### Don't
- **Avoid mixing saturated colors for body text** — Reserve vibrant accent colors exclusively for CTAs and highlights.
- **Don't use small radius (< 4px) on large containers** — Maintains visual hierarchy and coherence.
- **Avoid thick borders (> 2px) except on accent states** — Keep UI lightweight and modern.
- **Don't place dark text on dark backgrounds** — Ensure minimum contrast of 4.5:1 for accessibility.
- **Avoid padding below 12px inside interactive elements** — Maintain minimum 44px touch target height.
- **Don't mix serif and sans-serif in same context** — Stick to Geist/Inter pairing for consistency.
- **Avoid blur effects on text** — Maintain crisp readability, especially for technical content.
- **Don't shadow stack (multiple overlapping shadows)** — Use a single, well-calibrated shadow per level.
- **Avoid random spacing increments** — Every gap must correspond to the spacing scale.
- **Don't hide focus states** — Keyboard navigation must be equally clear as mouse navigation.

## 8. Responsive Behavior

### Breakpoints

| Name | Width | Key Changes |
|------|-------|------------|
| Mobile | 320px–639px | Single column layout; full-width cards; navigation collapses to hamburger menu; font sizes reduce 10–15% |
| Tablet | 640px–1023px | 2-column grid; side nav collapses; cards expand to fill; font sizes reduce 5–10%; padding reduced to 16px–20px |
| Desktop | 1024px–1439px | 12-column grid active; full nav visible; max container width 1224px; full font sizes; standard padding 24px–32px |
| Large Desktop | 1440px+ | Same as desktop with additional horizontal padding to maintain max-width container |

### Touch Targets

- **Minimum height:** `44px` for all interactive elements (buttons, links, inputs)
- **Minimum width:** `44px` for icon buttons and small interactive regions
- **Padding around touch targets:** `8px` minimum to prevent accidental activation
- **Spacing between buttons:** `16px` minimum to avoid mis-taps
- **Hover targets on desktop:** May be smaller than touch targets; apply hover pseudo-classes liberally

### Collapsing Strategy

**Desktop to Tablet:**
- Multi-column grids (3 or 4 columns) collapse to 2-column layouts
- Large hero sections reduce height by 20–30%
- Navigation menu transitions from horizontal top bar to sticky top bar with reduced height
- Font sizes reduce by 5–10%
- Padding/margins scale down by 1–2 units (e.g., `32px` → `24px`)
- Feature comparison tables become scrollable horizontally

**Tablet to Mobile:**
- All multi-column grids collapse to single column (100% width)
- Hero text reduces further; H1 becomes 48px (from 68px)
- Navigation collapses to hamburger menu (off-canvas or collapsible)
- Card padding reduces to `16px` from `28px–32px`
- Button widths expand to 100% of container (full-width stacked buttons)
- Code blocks scroll horizontally; font size reduces to 11px
- Vertical spacing between sections reduces by 1–2 units (e.g., `40px` → `24px`)
- Top/bottom padding on hero and major sections reduces to `32px` from `48px–64px`

**Mobile-Specific Adjustments:**
- All interactive elements must be minimum `44px × 44px`
- Tap-target spacing (`16px`) is enforced more strictly
- Bottom margin on cards and sections increases to `20px` (more breathing room on small screens)
- Sticky navigation uses simplified layout; logo smaller, nav icons instead of text
- Modal dialogs adapt to 100% viewport width with `16px` margin on sides

## 9. Agent Prompt Guide

### Quick Color Reference

- **Primary CTA:** Brand Orange (`#FF521D`) — All primary action buttons, hero highlights, brand emphasis
- **Secondary CTA:** Ghost/Bordered Orange (`#FF521D` 85% opacity) — Secondary buttons, alternate actions
- **Success Indicator:** Success Green (`#4ED996`) — Positive states, confirmations, approval badges
- **Warning Indicator:** Warning Amber (`#FFB84D`) — Caution states, non-critical alerts, attention flags
- **Information:** Sky Blue (`#7BD3F7`) — Info callouts, linked data, secondary messaging
- **Primary Background:** Almost Black (`#18181A`) — Page background, navigation base
- **Secondary Background:** Deep Charcoal (`#161618`) — Card backgrounds, container defaults
- **Tertiary Background:** Dark Slate (`#242426`) — Elevated card backgrounds, nested containers
- **Code Background:** Deeper Black (`#0F0F11`) — Code blocks, technical containers
- **Primary Text:** Pure White (`#FFFFFF`) — Primary heading and body text on dark backgrounds
- **Secondary Text:** Light Gray (`#F5F5F5`) — Secondary body text, reduced emphasis
- **Tertiary Text:** Zinc Gray (`#A1A1AA`) — Captions, metadata, muted UI labels
- **Disabled Text:** Medium Gray (`#A6A6A6`) — Disabled states, placeholder text
- **Border Subtle:** Transparent White (`rgba(255, 255, 255, 0.1)`) — Soft dividers, card borders
- **Border Medium:** Transparent White (`rgba(255, 255, 255, 0.15)`) — Elevated card borders, stronger dividers
- **Accent Highlight:** Electric Lime (`#E2FF7A`) — Bright accent highlights, neon-style emphasis on code

### Iteration Guide

1. **All primary CTAs must use `#FF521D`** with `12px 24px` padding, `10px` border radius, and `#FF521D 0px 6px 20px -6px` shadow on hover. No exceptions.

2. **Typography hierarchy is strict:** H1 at `68px/700wt/Geist`, H2 at `56px/700wt/Geist`, H3 at `28px/600wt/Geist`, body at `19px/400wt/Inter`. Deviation requires explicit justification.

3. **Dark mode is the default:** All backgrounds default to `#18181A` (page) or `#161618` (cards) unless explicitly stated otherwise.

4. **Spacing is always a multiple of 4px:** No arbitrary values. Scale from `4px`, `8px`, `12px`, `16px`, `24px`, `32px`, `40px`, `48px`. Double-check every gap.

5. **Contrast minimum is 4.5:1 for all readable text** on any background. White text on dark backgrounds is standard; use `#F5F5F5` or `#FFFFFF` only.

6. **Interactive elements (buttons, links, inputs) must be minimum `44px` height** on mobile and `40px` on desktop. Touch targets must have `16px` minimum spacing.

7. **Border radius follows the hierarchy:** `0px` (none), `4px` (small), `8px` (standard), `10px` (buttons), `12px` (cards). Do not invent intermediate values.

8. **Form inputs default to `#0F0F11` background** with `rgba(255, 255, 255, 0.15)` border. Focus state adds `1px solid #FF521D` border and `0px 0px 0px 3px rgba(255, 82, 29, 0.15)` shadow.

9. **Navigation bar is always sticky at top**, `56px` height, `#18181A` background, with `16px` horizontal padding and left-aligned logo, right-aligned links.

10. **Shadows are intentional and sparse:** Flat (`0px`), Raised (`0px 2px 4px`), Elevated (`0px 4px 12px`), High (`0px 8px 24px`). Orange glow (`#FF521D 0px 6px 20px -6px`) reserved for primary buttons only.

11. **Font families are non-negotiable:** Geist for headings, Geist Mono for tabs/badges/code, Inter for body/UI. Never mix serif or other sans-serif without written approval.

12. **Responsive breakpoints are 320px, 640px, 1024px, 1440px.** Mobile-first approach: design at 320px baseline, scale up. Collapse multi-column grids to single column below 640px.