# Supervenient — Brand & Design System (v0.6)

> Primary spec in Markdown; machine-readable companion is `supervenient-design-tokens.json` (W3C Design Tokens format, framework-agnostic — no Tailwind).
> Two audiences: humans skim the prose; agents read the JSON and the paste-in block (§17).
> Constraint: the **minimum** system that lets us build consistently.
> Contrast values target WCAG 2.2 AA; verify exact ratios with a checker before launch.
>
> **Changelog**
> - v0.4–v0.5: earlier blue-anchored system (sky/peach/mint/lilac on navy) with an additive "orb" motif. *Superseded.*
> - **v0.6: major direction change.** New jewel palette on a **purple core**, organised as three tiers — **ground · facets · spark**. The motif moves from the orb to the **kaleidoscope / convergence** (parts resolving into a whole). Yellow is promoted from a failed accent to a rationed **spark**. Neutrals are now purple-tinted; shadows are aubergine-tinted.

---

## 1. The idea

*Supervenience* — a higher-order whole (a team's shared understanding) **emerges from and depends on** the parts beneath it (people, their work). The colour system is built to say exactly this:

- **Ground** (purple) — the substrate everything rests on.
- **Facets** (gold, green, teal) — the parts: people, categories, contributions.
- **Spark** (yellow) — the single luminous point where the facets converge. The whole.

The motif is the **kaleidoscope**: many facets arranging into one symmetric pattern that exists only in the arrangement. Shift a facet and the whole resolves differently. The hub-and-spoke **convergence emblem** — facets meeting at a spark — is the brand in one image.

---

## 2. Behavioural foundations

The look is bold; the behaviour stays disciplined. Name these so trade-offs can be reasoned about.

- **Calm Technology (Weiser, Amber Case).** Inform without demanding attention; live in the periphery until needed; degrade gracefully. A bold palette does not mean a loud interface.
- **Cognitive-load reduction & progressive disclosure.** Show what matters now; reveal depth on intent.
- **Aesthetic–usability effect.** Considered visuals earn trust — doubly important for an AI teammate.
- **Isolation (Von Restorff) effect.** One salient element on generous space reads instantly. This is the spark, and the discipline behind it.
- **Trust mechanics for AI:** transparency (sources/reasoning), predictability (no surprises), control (editable, dismissible, reversible).
- **Blameless, anti-dark-pattern ethic.** Errors never blame the user; never manufacture urgency.
- **60-30-10 distribution.** ~60% ground/neutral, ~30% structure, ~10% facets — and the spark is a fraction of that 10%.

---

## 3. Personality & voice

Confident, clear, quietly intelligent. Plainspoken, short declarative sentences. Warm but unfussy; human, never corporate. The cleverness is in the thinking, not the volume.

**Avoid:** hard-sell, hype adjectives, feature-dumping, urgency, exclamation marks.

---

## 4. Design principles

1. **Bold, but disciplined** — saturated jewel facets and a deep ground, deployed with restraint (60-30-10).
2. **Centred, not cornered** — intelligence sits in the shared middle of the work, never a docked widget.
3. **Parts and whole** — facets are the parts; the spark is the whole, rationed to one point at a time.
4. **Present, then recede** — surface intelligence when useful; step back when not.
5. **One shared truth** — a single legible shared view over scattered panels.
6. **Depth carries the jewels** — luminous facets and the spark read on deep grounds; keep functional surfaces solid.

---

## 5. Colour

### 5.1 The three tiers

| Tier | Role | Members |
|---|---|---|
| **Ground** | substrate — text, deep surfaces, dark canvas | core purple, depth |
| **Facets** | the parts — fills, categories, areas | gold, green, teal (+ optional magenta) |
| **Spark** | the whole — rare convergence point | yellow |

### 5.2 Colour theory

The core `#4F2270` is a deep violet (H275 S53 L29) — it reads as mind, depth and sophistication, and anchors as a velvet ground that makes jewels glow. The facets sit around the wheel as a balanced jewel set: gold (warm), green and teal (cool), with optional magenta — warm/cool balanced, distinct in hue, and harmonious in gradients (the dichroic/kaleidoscope blend). Yellow is kept out of the facet set on purpose: it is invisible on white (~1.1:1) and overwhelming as a fill, which is exactly why it works as a singular spark on a deep ground (~11:1).

### 5.3 Ground

| Token | Hex | Role |
|---|---|---|
| `color.ground.core` | `#4F2270` | Brand purple — primary text, mid surfaces (≈11.6:1 on white) |
| `color.ground.depth` | `#241036` | Deep aubergine — dark canvas, hero, the ground jewels glow against |
| `color.ink` | `#4F2270` | Default body/heading text (= core; calm violet, not pure black) |

### 5.4 Neutrals (purple-tinted)

| Token | Hex | Use |
|---|---|---|
| `neutral.0` | `#FFFFFF` | — |
| `neutral.canvas` | `#FBFAFD` | App background (faint violet white) |
| `neutral.50` | `#F4F1F8` | Subtle surface |
| `neutral.100` | `#ECE7F2` | Cards / raised surface |
| `neutral.200` | `#DED5EA` | Borders, dividers |
| `neutral.400` | `#9C90AE` | Placeholder / disabled (non-essential) |
| `neutral.600` | `#5E5470` | Secondary text (~7:1 on white) |

### 5.5 Facets

Decorative values are **fills, facets and gradients** — not text on white. Use **ink** variants for text/icons/UI; **on-dark** for elements on the depth ground.

| Facet | Decorative | Ink (text/UI on white) | On-dark |
|---|---|---|---|
| Gold (warm lead) | `#FFC000` | `#8A5E00` | `#FFC000` |
| Green | `#8ED973` | `#1E7A3E` | `#8ED973` |
| Teal (cool) | `#2FB6D4` | `#0E7088` | `#2FB6D4` |
| Magenta (optional 4th) | `#D45BB0` | `#9A2F80` | `#D45BB0` |

Rules: **blend facets in gradients, don't tile flat blocks**; reserve one facet to dominate per view; gold is the only warm facet — use it for human, encouraging moments.

### 5.6 Spark — `#FFFF00`

The most powerful colour in the set *because* it is rationed. It marks one thing: the point where facets converge (the whole, the live signal, the one that matters).

- **Point scale only** — a node, marker, or single highlight. Never a fill or large area.
- **Dark grounds only** — reads on `ground` or darker; invisible on white.
- **One per view** — scarcity is the meaning. A second spark cancels the first.
- **Never text, never semantic** — it is *not* a warning colour (warning uses gold-ink + icon).

### 5.7 Semantic / functional colours

Three of the four semantics share a hue with a facet, so **meaning must always be carried by an icon and text — colour is reinforcement, never the signal.** Danger (red) is the one chromatically distinct from the brand, and the spark is never used semantically.

| Role | Strong (text/icon) | Surface | On-dark |
|---|---|---|---|
| Danger | `#B3261E` | `#FBEAE8` | `#FF9A90` |
| Warning | `#8A5E00` (gold-ink) | `#FDF1D6` | `#FFC000` |
| Success | `#1E7A3E` (green-ink) | `#E9F8E6` | `#8ED973` |
| Info | `#0E7088` (teal-ink) | `#DBF1F6` | `#2FB6D4` |

### 5.8 Dark mode

Map, don't invert. On `depth`: text `#FFFFFF` / `#C9BBDD`; surfaces lighten in steps (`#341852`, `#432063`); facets/spark use the **on-dark** values (vivid on aubergine); borders `rgba(255,255,255,0.12)`.

### 5.9 Accessibility (non-negotiable)

- Text ≥ 4.5:1 (large/UI ≥ 3:1). Decorative facets never carry essential text on white — use ink variants.
- **Never rely on colour alone** — pair semantic colour with icon and/or text (especially given facet/semantic hue overlap).
- **Focus ring always visible:** `#7B4BA8` (light) / `#2FB6D4` (dark), 2px solid + 2px offset (≥3:1 against background).
- Touch targets ≥ 44×44px; body text ≥ 16px.

---

## 6. Motif — kaleidoscope & convergence

The signature is the **kaleidoscope**: facets arranged into a symmetric whole, with a luminous centre. Its applied form is the **convergence emblem** — facet nodes joined by spokes to a central spark.

- **Facets blend** like dichroic glass — gradients (gold→green→teal→ground) read as one continuous surface. Use for hero panels, dividers, section breaks.
- **Ground rule (load-bearing).** Luminous effects — facet blends, the kaleidoscope, and the spark — only read on a **deep ground** (≈ `depth` or darker). On light surfaces use solid facet fills, ink variants and soft tints; do not expect glow on white.
- **Discipline.** The motif lives in imagery, brand surfaces and the convergence/AI signal. Functional UI surfaces stay solid for legibility; never put text over a busy facet blend.

---

## 7. Signalling AI

AI is the intelligent layer in the middle of the work — never an avatar, persona, or chatbot. Its visual signature is **convergence**: facets resolving toward a centre, marked at point scale by the spark.

- *Ambient* — AI available/underlying: a quiet presence at the relevant surface.
- *Active* — AI working/contributing: the convergence brightens.
- *Resolved* — output settled into the work: a quiet attribution cue.

**Surface-aware** (consequence of §6): the luminous convergence/spark reads on deep surfaces; over light content the signal becomes a soft facet tint plus an accent edge — same meaning, technique adapts to the ground. Everything the AI produces is editable, dismissible and reversible; show uncertainty and sources; honour `prefers-reduced-motion`.

---

## 8. Imagery

Jewel-toned, kaleidoscopic, refractive — dichroic glass, faceted symmetry, a luminous convergent centre. Built from the facets on `ground`/`depth`. The convergence emblem is the hero device. Avoid stock laptop photography, clip-art, neon overload, and busy compositions.

---

## 9. Typography

**Lexend** throughout. Headings Medium (500) tracked in; body Regular (400) airy.

| Style | Size / line-height | Weight | Tracking |
|---|---|---|---|
| Display | 48 / 1.10 | 500 | -0.03em |
| H1 | 36 / 1.15 | 500 | -0.025em |
| H2 | 28 / 1.20 | 500 | -0.02em |
| H3 | 22 / 1.30 | 500 | -0.01em |
| Body L | 18 / 1.55 | 400 | 0 |
| Body | 16 / 1.55 | 400 | 0 |
| Small | 14 / 1.45 | 400 | 0 |
| Caption | 12 / 1.40 | 400 | 0 (sparingly) |

Emphasise via weight and size, not colour or underlines. No heavy bold, no all-caps. Sentence case everywhere.

---

## 10. Space, radius, elevation, motion

```
spacing: 2, 4, 8, 12, 16, 24, 32, 48, 64, 96   (base 4; rhythm 8)
radius:  sm 6 · md 10 · lg 16 · xl 24 · pill 999
```

Elevation — diffuse, aubergine-tinted shadows (never pure black):
```
e1: 0 1px 3px rgba(36,16,54,.12), 0 1px 2px rgba(36,16,54,.07)
e2: 0 6px 20px rgba(36,16,54,.12)
e3: 0 16px 48px rgba(36,16,54,.22)
```

Motion — calm and brief: 120 / 180 / 240ms; decelerate easing `cubic-bezier(0.2, 0, 0, 1)`. Always honour `prefers-reduced-motion` (the kaleidoscope's slow rotation stops).

---

## 11. Iconography

Line icons, ~1.75px stroke, rounded caps/joins to match Lexend. Filled variants for active/selected. 24px grid. Geometric and calm, never busy.

---

## 12. Component states

Define for every interactive component: **default, hover, active, focus, disabled, loading, error, empty, success.** Hover/active = small tint shift, not a colour swap. Disabled = `neutral.400` on `neutral.100`. Loading = calm shimmer (no anxious spinners). Empty = a gentle invitation with one action. Error/Success = semantic colour + icon + plain text.

---

## 13. UX writing, microcopy & locale

- **Blameless, plain errors:** what happened + next step. "We couldn't save that — try again."
- **Empty states invite:** "Start a brief and the team will see it here."
- **AI copy is honest:** tentative where uncertain; never overclaims.
- **Locale (UK):** £, dates DD/MM/YYYY, en-GB spelling (organise, colour, prioritise).

---

## 14. Data visualisation

Use facet **ink/decorative** variants in a fixed, colour-blind-safe order, always with labels. Reserve the spark for a single highlighted point — the one that matters.

```
categorical: #FFC000 (gold) · #2FB6D4 (teal) · #8ED973 (green) · #D45BB0 (magenta) · #4F2270 (purple)
sequential:  tints of teal  #DBF1F6 → #2FB6D4 → #0E7088 → #241036
highlight:   #FFFF00 (spark) — one point only, on a deep chart ground
```

Minimal chart chrome: thin axes `neutral.200`, labels `neutral.600`, generous spacing.

---

## 15. Logo notes (interim — full brand work to follow)

Wordmark in Lexend Medium, tracked in (-0.025em): **Supervenient**. The **convergence emblem / kaleidoscope** is the symbol and favicon. Minimum clear space = emblem height on all sides. Keep the wordmark `ink` on light or white on `depth`; don't recolour it in facets.

---

## 16. Quick do / don't

**Do:** purple (`#4F2270`) default text · blend facets in gradients · ink variants for facet text/UI · the spark at point scale on a deep ground, once · semantic colour + icon + text · a visible focus ring · solid functional surfaces · plain, blameless copy.

**Don't:** pure-black body text · facet text on white · tile flat facet blocks · spark as a fill, on white, or as a warning · rely on colour alone · expect glow on light grounds · strip focus states · dense dashboards · hype copy.

---

## 17. Paste-in block for agentic interface generation

```
BRAND: Supervenient — AI as the intelligent layer in the middle of a team's work. Concept:
supervenience — a whole that emerges from its parts. Colour mirrors this in three tiers:
GROUND (purple substrate) · FACETS (the parts) · SPARK (the convergence point / the whole).
Motif: kaleidoscope / convergence emblem (facets resolving to a centre). Principles: Calm
Technology, progressive disclosure, present-then-recede, one shared source of truth, blameless,
no dark patterns. Bold but disciplined; 60-30-10 distribution.

FONT: Lexend. Headings Medium(500), letter-spacing -0.025em, sentence case. Body Regular(400),
line-height 1.55, min 16px. Emphasise via weight/size, not colour. No all-caps, no heavy bold.
Scale: Display48 H1:36 H2:28 H3:22 BodyL:18 Body:16 Small:14.

COLOUR
ground:  core #4F2270 (text + mid surfaces) | depth #241036 (dark canvas) | ink = #4F2270
neutrals (purple-tinted): canvas #FBFAFD | 50 #F4F1F8 | 100 #ECE7F2 | 200 #DED5EA(borders)
          | 400 #9C90AE(disabled) | 600 #5E5470(secondary text)
facets — DECORATIVE only (fills/gradients, NOT text on white); use ink for text/UI:
  gold  #FFC000 / ink #8A5E00      green #8ED973 / ink #1E7A3E
  teal  #2FB6D4 / ink #0E7088      magenta #D45BB0 / ink #9A2F80 (optional)
SPARK #FFFF00 — the whole. POINT SCALE ONLY, DARK GROUND ONLY, ONE PER VIEW. Never text, never
  a fill, never a warning colour. Invisible on white by design.
semantic (always icon+text; hue overlaps facets so colour is reinforcement only):
  danger #B3261E/surf #FBEAE8 | warning #8A5E00/surf #FDF1D6 | success #1E7A3E/surf #E9F8E6 |
  info #0E7088/surf #DBF1F6
focus ring: #7B4BA8 light / #2FB6D4 dark, 2px solid + 2px offset (always visible).

GROUND RULE: luminous effects (facet blends, kaleidoscope, spark) only read on a DEEP ground
(>= depth). On light surfaces use solid facet fills, ink variants and soft tints — no glow on white.

LAYOUT: spacing 4/8/12/16/24/32/48/64/96; radius 6/10/16/24/pill; diffuse aubergine-tinted shadows
(no pure black). Generous whitespace, one focal point, 1-2 columns, minimal borders.
Motion 120-240ms, decelerate easing, honour prefers-reduced-motion.

MOTIF: kaleidoscope / convergence emblem — facet nodes joined to a central spark. Facets blend
like dichroic glass in gradients on a deep ground.

AI: the intelligent layer in the middle (inline, contextual), never a corner chatbot/avatar. Signal
= convergence: ambient -> active -> resolved. Surface-aware (glow on dark; soft tint+edge on light).
Editable/dismissible/reversible; show uncertainty + sources.

ACCESSIBILITY: WCAG 2.2 AA. Text >=4.5:1 (large/UI >=3:1). Never colour-only meaning. Visible focus.
Touch >=44px. Body >=16px.

VOICE & COPY: calm, clear, plainspoken. Short declarative sentences. Errors blameless and plain.
Empty states invite. en-GB spelling, £, DD/MM/YYYY. No hype, no exclamation marks.
```

---

*Version 0.6 — ground · facets · spark. A deliberately minimal system; verify all contrast pairs with a checker before launch.*