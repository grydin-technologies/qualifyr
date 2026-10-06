# Qualifyr – image-generation prompts

Prompts for producing the visual assets the landing page still uses placeholders for.
Copy a prompt into your image generator of choice (ChatGPT/DALL·E, Midjourney, Ideogram).

**Brand constraints – apply to every prompt:**
- **Strictly black and white / greyscale. No colour, no gradients of hue.** The Qualifyr
  accent is monochrome (`--brand` is pure black in light mode, pure white in dark). Any
  colour will clash with the site.
- Minimal, geometric, modern SaaS. Think Linear / Vercel / Stripe restraint, not clip-art.
- Flat vector look, clean edges, generous negative space. No photorealism, no 3D bevels,
  no drop shadows baked in, no busy detail.
- Where it says *transparent background*, ask for PNG with transparency (or export SVG).

> Note on SVG: image generators output raster (PNG), not true SVG. For the **logo mark and
> favicon** I'd rather hand-code the SVG directly – it's geometric and monochrome, so I can
> make it pixel-crisp and themeable instead of generating a fuzzy raster. Say the word and
> I'll do that in code. The prompts below are for the illustration-style assets where a
> generator genuinely helps (OG image, auth/FAQ art, hero backdrop).

---

## 1. Logo mark / app icon

> A minimalist black-and-white app icon for a B2B software product called "Qualifyr", a lead
> qualification engine. Abstract geometric mark suggesting a funnel filtering many dots down
> to a few highlighted ones – the idea of separating real buyers from noise. Single-weight
> line work or a solid silhouette, centered, on a transparent background. Flat vector, no
> colour, no gradient, no shadow. Bold enough to read clearly at 32×32 px. Square.

Variations to try: swap "funnel filtering dots" for "a target reticle with one dot locked
in", or "a checkmark formed out of a downward filter". Pick whichever reads at favicon size.

## 2. Wordmark (optional – text logo)

> The word "Qualifyr" as a clean, modern wordmark in a geometric sans-serif, solid black on
> transparent background (and a white-on-transparent variant). Tight, confident letter
> spacing. No icon, no tagline, no effects. Horizontal lockup.

## 3. Open Graph / social share image (1200 × 630)

> A 1200×630 social share banner for "Qualifyr", a buyer-only B2B lead engine for Pakistan
> and the GCC. Pure black background. Large white headline text "See who actually buys."
> in a clean geometric sans-serif, upper-left. Small monochrome funnel/target logo mark. A
> faint, subtle abstract grid or dotted texture in dark grey in the lower-right, evoking a
> data pipeline. Lots of negative space, high contrast, minimal, premium. No colour.

## 4. Auth panel illustration (vertical, split-screen sign-in side)

> A tall vertical illustration for the side panel of a sign-in screen. Monochrome
> (black/white/grey only). Abstract depiction of qualified leads: a loose column of small
> company "cards", a few highlighted with a subtle score badge, connected by thin lines into
> a single funnel. Calm, editorial, lots of dark negative space so white UI text overlays
> cleanly on top. Flat vector, no colour, no photorealism. Portrait orientation ~4:5.

## 5. FAQ spot illustration (optional, small)

> A small square monochrome spot illustration: a single speech bubble made of thin geometric
> lines with a question mark resolving into a checkmark. Minimal, black on transparent, lots
> of white space. Flat vector, no colour.

## 6. Hero backdrop texture (optional, very subtle)

> A very subtle, dark, seamless background texture for a website hero on a near-black page.
> Faint dark-grey dotted grid or fine topographic contour lines, extremely low contrast, no
> focal point – it must sit quietly behind white headline text without competing. Pure
> greyscale, no colour, no bright areas. Wide 16:9.

---

## Where each asset goes

| Asset | File / usage |
|---|---|
| Logo mark | `web/src/app/icon` + nav logo (currently a lucide icon) |
| Favicon | `web/src/app/favicon.ico` |
| OG image | replaces the generated `web/src/app/opengraph-image.tsx` (or sits beside it) |
| Auth panel art | `web/src/app/(auth)/layout.tsx` side panel |
| FAQ art | `web/src/components/marketing/faq.tsx` (optional) |
| Hero backdrop | `web/src/components/marketing/hero.tsx` (optional) |

After you generate them, hand me the files (or drop them in `web/public/`) and I'll wire
each into the right place and confirm they theme correctly in light and dark.
