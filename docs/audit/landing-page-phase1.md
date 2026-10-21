# Landing Page Audit — Phase 1 (Baseline)

**Page:** `docs/index.html`
**Live:** https://kenjaku-dev.github.io/pymon/
**Analyzer:** `website-audit` + `usability`

## Baseline Report

| Dimension | Score | Notes |
|-----------|-------|-------|
| Content & structure | 8/10 | Clear hero, features, install, keys, FAQ, final CTA. Order logical. |
| Conversion/CTA | 6/10 | Primary CTA visible; secondary CTA weak; no comparison/social proof; one CTA style only. |
| Visual design | 7/10 | Cohesive terminal style; emoji icons; minimal design system, spacing okay. |
| Typography | 6/10 | Body font sizes below 18px in several sections; subheadings fine. |
| Accessibility | 4/10 | Several low-contrast colors, no skip link, no focus styles, no ARIA on accordion. |
| Performance | 9/10 | 13 KB single file, no scripts/images/render-blocking. |
| SEO basics | 6/10 | Title/description present; missing OG tags, favicon, structured data, sitemap/robots. |
| Mobile | 7/10 | Single-column fallback; nav links hidden rather than collapsed; terminal scroll okay. |

**Overall baseline: 6.6/10**

## Key Issues (Prioritized)

### High priority
1. **Contrast — muted (#555) too dark** on black backgrounds (≈2.8:1 vs black, ≈2.5:1 vs surface). Fails 4.5:1. Likely affects meta text, muted body copy, footer, code comments.
2. **Body text size < 18px** in features/kbd/install sections (13–14px). Measured usability guideline says ≥18px for readable content.
3. **No visible focus styles** for keyboard users; no `:focus-visible` states on buttons/links/accordion.
4. **No OG image/meta**, favicon, or structured data — social sharing looks bare.

### Medium priority
5. Emoji icons for feature cards → replace with inline SVGs (per icon) for a modern technical look.
6. Fake terminal mock instead of real screenshot/GIF — lower authenticity than real UI capture.
7. No comparison table with conventional monitors (htop, btop) — misses opportunity to differentiate.
8. Nav links hidden on mobile rather than a compact menu — acceptable but small UX gap.

### Low priority
9. Missing sitemap.xml / robots.txt (GitHub Pages can serve).
10. No back-to-top helper; long page scroll from FAQ to top.
11. No GitHub star badge / social proof.
12. Reduced-motion support not declared (uses smooth scroll and transitions).

---

## Content Notes
- Hero communicates value well; install section is concrete (good).
- Add a "Why not htop?" comparison for technical audience.
- Add real screenshots (TUI export) to strengthen authenticity.
- FAQ detail text is informative, needs styling/audio contrast.

---

## Success Criteria for Phase 2+
- Raise overall score to **≥8.5/10**.
- Contrast ≥4.5:1 everywhere.
- Body text ≥18px.
- Visible focus styles + reduced-motion respect.
- Add OG/favicon + one real screenshot section.
- Add comparison table.
