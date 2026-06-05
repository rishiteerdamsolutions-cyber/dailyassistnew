---
name: AHA Design System
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#434656'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#737688'
  outline-variant: '#c3c5d9'
  surface-tint: '#004dea'
  primary: '#0041c8'
  on-primary: '#ffffff'
  primary-container: '#0055ff'
  on-primary-container: '#e3e6ff'
  inverse-primary: '#b6c4ff'
  secondary: '#565e74'
  on-secondary: '#ffffff'
  secondary-container: '#dae2fd'
  on-secondary-container: '#5c647a'
  tertiary: '#415166'
  on-tertiary: '#ffffff'
  tertiary-container: '#596980'
  on-tertiary-container: '#dbe9ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dce1ff'
  primary-fixed-dim: '#b6c4ff'
  on-primary-fixed: '#001551'
  on-primary-fixed-variant: '#0039b3'
  secondary-fixed: '#dae2fd'
  secondary-fixed-dim: '#bec6e0'
  on-secondary-fixed: '#131b2e'
  on-secondary-fixed-variant: '#3f465c'
  tertiary-fixed: '#d3e4fe'
  tertiary-fixed-dim: '#b7c8e1'
  on-tertiary-fixed: '#0b1c30'
  on-tertiary-fixed-variant: '#38485d'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
  deep-navy: '#0F172A'
  slate-gray: '#475569'
  action-blue: '#0055FF'
  success-green: '#10B981'
  border-subtle: '#E2E8F0'
typography:
  headline-xl:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Geist
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Geist
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 14px
    letterSpacing: 0.04em
  mono-md:
    fontFamily: jetbrainsMono
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 8px
  gutter: 24px
  margin-desktop: 80px
  margin-mobile: 20px
  max-width: 1200px
---

## Brand & Style

The brand personality for the design system is defined by **Precision, Reliability, and Quiet Intelligence**. As a desktop utility that "sees" the screen to assist users, the UI must avoid the hyper-active, glowing "AI" tropes (robotic mascots, neon gradients, or complex dashboard visualizations) in favor of a **Corporate Modern** aesthetic that feels like a native extension of a high-end operating system.

The style leverages **Minimalism** to ensure the user feels in control, not overwhelmed. It draws inspiration from premium productivity tools: heavy use of whitespace, refined typography, and a "utilitarian-luxe" feel. The emotional goal is to evoke a sense of calm efficiency—moving from the friction of a task to the "Aha!" moment of completion.

**Visual Principles:**
- **Clarity over Decoration:** Every element exists for a functional reason. 
- **Subtle Depth:** Use of light and shadow to create a clear "Utility" layer above the user's content.
- **Human-Centric:** Imagery should focus on clean hardware (laptops) and clear chat interfaces, emphasizing the partnership between human and assistant.

## Colors

The palette is anchored in **Deep Navy** and **Slate Gray** to establish professional authority and trust. These colors provide the structural "weight" of the interface. 

**Action Blue** is reserved exclusively for primary interactions, ensuring the user's eye is always drawn to the next step (Subscribe, Download, or Send). 

- **Primary (Action Blue):** Used for buttons, active states, and focus indicators.
- **Secondary (Deep Navy):** Used for high-level headings and the primary navigation background to provide a solid foundation.
- **Tertiary (Slate Gray):** Used for secondary text, icons, and supporting UI elements.
- **Neutral:** A very light, cool-toned gray is used for backgrounds to reduce eye strain compared to pure white, maintaining the "calm" atmosphere.

Avoid using gradients or vibrating color combinations. Success and error states should be handled with muted, professional versions of green and red.

## Typography

The typography system is designed for high legibility and a technical, yet approachable feel. 

- **Headlines:** Use **Hanken Grotesk** for its clean, contemporary geometry. It provides a "modern utility" feel that distinguishes the marketing site from standard corporate templates.
- **Body:** Use **Inter** for all long-form text. It is the gold standard for screen readability and maintains a neutral, professional tone.
- **Labels/UI Elements:** Use **Geist** for buttons, tabs, and small UI metadata. Its technical precision reinforces the "computer assistance" nature of the product.
- **Code/Technical Data:** For mentions of API keys or technical steps, **JetBrains Mono** should be used sparingly to provide a clear visual distinction for "technical" content.

Maintain tight tracking (letter spacing) on large headlines to keep them feeling impactful and modern, while increasing line height for body text to ensure a comfortable reading experience.

## Layout & Spacing

This design system utilizes a **Fixed Grid** for marketing content to ensure an editorial, "high-end" feel, while allowing for fluid behavior in the application-style checkout and download areas.

**Grid System:**
- **Desktop:** 12-column grid with a max-width of 1200px. Gutters are fixed at 24px to provide "breathing room" between content blocks.
- **Tablet:** 8-column fluid grid with 20px margins.
- **Mobile:** 4-column fluid grid with 16px margins.

**Spacing Rhythm:**
A strict 8px base unit is used for all padding and margins. Use "Generous Whitespace" as a core design principle—sections should be separated by at least 80px-120px on desktop to prevent the site from feeling cluttered or "salesy." Component-internal spacing should follow the `base * n` rule (e.g., 16px, 24px, 32px).

## Elevation & Depth

To achieve the "Premium Desktop Utility" feel, the system uses **Ambient Shadows** and **Tonal Layers** instead of heavy borders.

- **Surface Tiers:**
  - **Level 0 (Background):** The neutral-colored base layer.
  - **Level 1 (Cards/Sections):** Pure white surfaces with a very soft, diffused shadow (15% opacity, 20px blur).
  - **Level 2 (Popovers/Tooltips):** A slightly more pronounced shadow with a thin `border-subtle` outline to ensure separation from Level 1.

**Shadow Character:**
Shadows should be tinted slightly with the `deep-navy` color to keep them feeling grounded and integrated into the palette, rather than looking like "dirty" gray smudges. Depth is used to guide attention, not just for decoration—elements that can be interacted with (like pricing cards) should sit "higher" than static content.

## Shapes

The shape language is **Rounded**, reflecting a modern software aesthetic while maintaining a sense of approachability. 

- **Standard Elements (Buttons, Inputs):** 0.5rem (8px). This creates a balanced look that is neither too sharp (aggressive) nor too round (childish).
- **Large Elements (Cards, Containers):** 1rem (16px). This differentiates layout containers from interactive components.
- **Interactive States:** On hover, primary buttons should maintain their roundedness but can scale slightly (1.02x) to provide tactile feedback without changing the shape's fundamental geometry.

## Components

### Buttons
- **Primary:** Solid `action-blue` with white text. Geist Medium font. 8px corner radius.
- **Secondary:** Ghost style with `deep-navy` text and a `border-subtle`. 
- **Sizes:** Large (56px height) for Hero CTAs, Medium (44px) for standard forms.

### Pricing Cards
- Use white backgrounds with Level 1 elevation.
- The "Pro" card should have a subtle 2px top-border in `action-blue` to signify it as the premium tier, without using aggressive "Best Value" badges.
- Use a simple vertical list with checkmarks in `action-blue` for features.

### Input Fields
- Background: Pure white.
- Border: 1px `border-subtle`.
- Focus State: 2px `action-blue` border with a subtle 4px blue outer glow (blur).
- Use **Geist** for placeholder text to maintain the technical utility feel.

### Chat Interface Snippets
- Since the product is an assistant, the marketing site should use stylized chat bubble components. 
- User messages: `deep-navy` background with white text.
- AHA messages: White background with Level 1 elevation and `action-blue` accent icon.

### Checkboxes & Radio Buttons
- Custom styled to match the `action-blue` primary color. 
- Use 4px corner radius for checkboxes to match the overall rounded language.

### Status Chips
- Used for "Mac" and "Windows" badges. Small, `geist` font, all-caps, with a light slate-gray background and dark text.