# Supervenient — Brand & Design System (v0.5)

> Primary spec in Markdown; the machine-readable companion is `supervenient-design-tokens.json` (W3C Design Tokens format, framework-agnostic — no Tailwind).
> Two audiences: humans skim the prose; agents read the JSON and the paste-in block (§17).
> Constraint: the **minimum** system that lets us build calmly and consistently.
> Contrast values target WCAG 2.2 AA; verify exact ratios with a checker before launch.
>
> Changelog v0.3: added colour-theory analysis (§5.1); introduced **layering & additive colour** as the core motif (§6); reframed the AI indicator from an "avatar/orb" to an **additive layer** that signals AI is in use (§7); demoted the orb to one expression of that language (§8).
> Changelog v0.4: deepened lilac from #EDBDE7 to #EAA4E0 (L84→L78, more chroma) so it is a true tonal peer of the other accents.
> Changelog v0.5: added the **ground rule** for additive colour — screen-blending only reads on a dark/deep surface; on light surfaces use soft tints or a depth panel (§6). Made the AI layer surface-aware (§7).

---

## 1. The idea

*Supervenience* — a higher-order thing (a team's shared understanding) **emerges from and depends on** the parts beneath it (people, their work, their conversation). The product thesis:

- The AI doesn't replace the team — it **arises from** their work and makes the whole greater than the parts.
- It sits **in the middle** of the work, not bolted on at the edges.
- Out of many inputs, one clear point of alignment emerges.

The visual language makes this literal through **layers**: translucent, overlapping fields where the overlap produces a new tone that existed in neither layer alone — the whole exceeding its parts. The orb is one expression of this (light refracting and converging to a luminous centre); the layer is the general principle.

---

## 2. Behavioural foundations

The aesthetic is a set of behavioural commitments — name them so trade-offs can be reasoned about.

- **Calm Technology (Weiser, Amber Case).** Inform without demanding attention; live in the periphery until needed; degrade gracefully. The north star.
- **Cognitive-load reduction & progressive disclosure.** Show only what matters now; reveal depth on intent. This *is* "present, then recede."
- **Aesthetic–usability effect.** Considered, calm visuals earn trust — doubly important for an AI teammate.
- **Isolation (Von Restorff) effect.** One salient element on generous space reads instantly.
- **Trust mechanics for AI:** transparency (sources/reasoning), predictability (no surprises), control (always editable, dismissible, reversible).
- **Blameless, anti-dark-pattern ethic.** Errors never blame the user; never manufacture urgency.
- **60-30-10 distribution.** ~60% canvas/neutral, ~30% depth/structure, ~10% accent.

---

## 3. Personality & voice

Calm, clear, quietly intelligent. Confident without hype. Plainspoken, short declarative sentences. Warm but unfussy; human, never corporate. Understated — cleverness in the thinking, not the volume. Spacious.

**Avoid:** hard-sell, hype adjectives, feature-dumping, urgency, nagging, exclamation marks.

---

## 4. Design principles

1. **Calm by default** — whitespace, soft edges, one clear action per view.
2. **Centred, not cornered** — intelligence in the shared middle, never a docked widget.
3. **Layers carry the meaning** — overlapping, additive colour expresses the underlying/emergent idea; light, not weight, does the emotional work.
4. **Present, then recede** — surface intelligence when useful; step back when not.
5. **One shared truth** — a single legible shared view over scattered panels.
6. **Soft, never harsh** — rounded forms, diffuse glows, minimal hard borders.

---

## 5. Colour

### 5.1 Does the palette work? (colour theory)

Yes — and deliberately. In HSL:

| Accent | H | S | L | Reads as |
|---|---|---|---|---|
| Peach `#F3AC89` | 20° | 82% | 75% | warm orange |
| Mint `#A1E9AB` | 128° | 62% | 77% | green |
| Sky `#93DAF7` | 197° | 86% | 77% | azure |
| Lilac `#EAA4E0` | 309° | 62% | 78% | magenta-pink |

- **Tetradic (rectangle) harmony — two complementary pairs.** Peach (20°) ≈ opposite Sky (197°); Mint (128°) is exactly opposite Lilac (308°). A balanced, intentional structure — and the reason gradients sit well while flat blocks can fight (tetradic schemes are the hardest to balance, so "blend, don't tile" + 60-30-10 are the right discipline).
- **Blue-anchored.** Navy `#0E2841` is H209 — the deep, desaturated version of the sky hue. Navy + sky form a structural backbone; peach + lilac are warm reliefs. Coherent by construction.
- **Hidden hierarchy in saturation.** Peach/sky are punchy (S82/86) → expressive **lead** pair; mint/lilac are soft (S62/57) → quieter **support** pair.
- **Lilac deepened for parity (resolved).** As originally supplied (`#EDBDE7`, L84) lilac was a pale outlier that nearly vanished on white. It is now `#EAA4E0` (L78, S62), a true peer of the other three. (Original retained here only for provenance.)

**Verdict:** a well-formed, blue-anchored tetradic palette, warm/cool balanced, with all four accents now tonally matched.

### 5.2 Relationships & usage rules

- **Blend accents, don't tile them.** Best as gradients and overlaps; flat complementary blocks side by side can vibrate.
- **Peach is the only warm hue** — reserve it for human, encouraging moments; lean cool/neutral elsewhere for calm.
- **Psychology:** navy → depth/competence; sky → clarity/trust; peach → warmth/approachability; mint → growth/safety; lilac → reflection/softness.

### 5.3 Core tokens

| Token | Hex | Role |
|---|---|---|
| `color.canvas` | `#FFFFFF` | Primary light background |
| `color.depth` | `#0E2841` | Deep brand dark — dark surfaces, dark-mode canvas, strongest text |
| `color.ink` | `#0E2841` | **Default body/heading text** (calm — navy, not pure black) |
| `color.black` | `#000000` | Reserved max-contrast only; not the default |

### 5.4 Neutral ramp (navy-tinted)

| Token | Hex | Use |
|---|---|---|
| `neutral.0` | `#FFFFFF` | Canvas |
| `neutral.50` | `#F6F8FA` | App background / subtle surface |
| `neutral.100` | `#ECEFF3` | Cards / raised surface |
| `neutral.200` | `#DCE2E9` | Borders, dividers |
| `neutral.400` | `#9AA5B3` | Placeholder / disabled (non-essential) |
| `neutral.600` | `#5B6675` | Secondary text (targets AA on white) |
| `neutral.900` | `#0E2841` | Primary text (= depth, AAA on white) |

### 5.5 Brand accents + accessible variants

Originals are **decorative** (gradients/fills/glow). For **text, icons or interactive UI**, drop to the accessible deep variant.

| Accent | Decorative | Accessible (text/UI on white) | On-dark |
|---|---|---|---|
| Sky (lead) | `#93DAF7` | `#1668B0` | `#93DAF7` |
| Peach | `#F3AC89` | `#B45A30` | `#F3AC89` |
| Mint | `#A1E9AB` | `#1E7A3E` | `#7FE0A0` |
| Lilac | `#EAA4E0` | `#9A4D8E` | `#EAA4E0` |

### 5.6 Semantic / functional colours

Kept separate from brand accents so meaning is never ambiguous (success/info intentionally echo mint/sky).

| Role | Strong (text/icon) | Surface | On-dark |
|---|---|---|---|
| Danger | `#B3261E` | `#FBEAE8` | `#FF9A90` |
| Warning | `#8A5A00` | `#FCF3E1` | `#F5C26B` |
| Success | `#1E7A3E` | `#E7F6EC` | `#7FE0A0` |
| Info | `#1668B0` | `#E6F3FC` | `#93DAF7` |

### 5.7 Dark mode

Map, don't invert. On `depth`: text `#FFFFFF` / `#B9C4D2`; surfaces lighten in steps (`#15314D`, `#1C3C5C`); accents/semantics use the **on-dark** columns; borders `rgba(255,255,255,0.12)`.

### 5.8 Accessibility (non-negotiable)

- Text ≥ 4.5:1 (large/UI ≥ 3:1). Decorative pastels never carry essential text on white.
- **Never rely on colour alone** — pair semantic colour with icon and/or text.
- **Focus ring always visible:** `#1668B0` (light) / `#93DAF7` (dark), 2px solid + 2px offset (≥3:1 against background).
- Touch targets ≥ 44×44px; body text ≥ 16px.

---

## 6. Layering & additive colour (the supervenience motif)

The signature device: **translucent layers that overlap, with a new tone emerging in the intersection** — the whole exceeding its parts.

- **Additive by default (screen blend) — on a dark ground.** Overlapping accents move *toward light*; screening the complementary pairs (sky+peach, mint+lilac) drives toward a luminous near-white — the orb's glowing centre, a visual of emergence.
- **Additive needs a deep ground (important).** Screen blending only reveals light against a dark/deep surface (≈ `depth` or darker). On a light surface it blows straight out to white and the layers disappear. So: **on dark → screen-blend and let overlaps glow; on light → use translucent _soft tints_ (normal alpha blend) or place the luminous layer over a `depth` panel.** Never screen-blend on a light background.
- **Avoid multiply for accents.** Multiplying complements collapses them into grey-brown mud. Reserve multiply/darken only for subtle neutral shadows (which do want a light ground).
- **Translucency:** expressive layers run ~40–70% opacity; the overlap reveals the emergent third tone. Ambient layers sit much fainter.
- **Layers should feel underlying.** Read top-to-bottom as strata: surface content sits *above* a softer layer that gives rise to it. This is the "supervenes on" relationship made visual.
- **Discipline (protects calm + legibility):** layering lives in imagery, ambient backgrounds, brand moments, and the AI indicator. **Functional UI surfaces stay solid** — never put body text over a busy overlap zone, and never let translucency drop text contrast below AA.

---

## 7. Signalling AI: the additive layer

AI is shown not as an avatar, persona, or chat character, but as **an additive layer over the underlying work** — a luminous stratum that depends on the content beneath it. This is avatar-free and chat-free, works anywhere AI is applied (inline edits, generated content, suggestions, background processing), and is itself the supervenience metaphor.

**Intensity scales with involvement; it never demands attention.**

- *Ambient* — AI available/underlying: a faint additive tint or edge at the relevant surface (`layer.opacity.ambient`).
- *Active* — AI working/contributing: the layer brightens, with gentle motion through the accent gradient (`layer.opacity.active`).
- *Resolved* — output has settled into the work: the layer fades to a quiet attribution cue.

**Surface-aware (consequence of the ground rule, §6):** the luminous screen-blended wash only reads on dark/deep surfaces. Over light content the *same* signal is expressed as a **soft accent tint plus an accent edge or border** — not a screen blend. The meaning (ambient → active → resolved) stays constant; only the technique adapts to the ground.

**Attribution & trust:** the presence of the additive accent layer distinguishes AI-touched content from human — quiet but legible. Everything the AI produces is editable, dismissible, and reversible. Show uncertainty and sources. Honour `prefers-reduced-motion` (no pulsing).

---

## 8. Imagery & the orb

The **orb / lens** is the fullest expression of the additive-layer language: light from many sources converging and refracting to a luminous centre. Use it for hero moments, loading/empty states, section breaks, and rich brand surfaces. Built from accent gradients on white or on `depth`. One orb, lots of room. The same language compresses elsewhere into an edge-glow, a corner tint, or a soft gradient underline. Avoid stock laptop photography, clip-art, neon overload, and hard geometric grids.

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

Elevation — diffuse, navy-tinted shadows (never pure black):
```
e1: 0 1px 3px rgba(14,40,65,0.10), 0 1px 2px rgba(14,40,65,0.06)
e2: 0 4px 12px rgba(14,40,65,0.08)
e3: 0 12px 40px rgba(14,40,65,0.12)
```

Motion — calm and brief: 120 / 180 / 240ms; decelerate easing `cubic-bezier(0.2, 0, 0, 1)`. Always honour `prefers-reduced-motion`.

---

## 11. Iconography

Line icons, ~1.75px stroke, rounded caps/joins to match Lexend and the soft brand. Filled variants for active/selected. 24px grid. Geometric and calm, never playful or busy.

---

## 12. Component states

Define for every interactive component: **default, hover, active, focus, disabled, loading, error, empty, success.** Hover/active = small tint shift, not a colour swap. Disabled = `neutral.400` on `neutral.100`. Loading = calm shimmer or the additive layer's active state (no anxious spinners). Empty = a gentle invitation with one action. Error/Success = semantic colour + icon + plain text.

---

## 13. UX writing, microcopy & locale

- **Blameless, plain errors:** what happened + next step. "We couldn't save that — try again," not "Error 422."
- **Empty states invite:** "Start a brief and the team will see it here."
- **AI copy is honest:** tentative where uncertain; never overclaims.
- **Locale (UK):** £, dates DD/MM/YYYY, en-GB spelling (organise, colour, prioritise).

---

## 14. Data visualisation

Use accessible-accent variants in a fixed, colour-blind-safe order, always paired with labels:
```
categorical: #1668B0 · #B45A30 · #1E7A3E · #9A4D8E · #5B6675
sequential:  #E6F3FC → #93DAF7 → #1668B0 → #0E2841
```
Minimal chart chrome: thin axes `neutral.200`, labels `neutral.600`, generous spacing.

---

## 15. Logo notes (interim — full brand work to follow)

Wordmark in Lexend Medium, tracked in (-0.025em): **Supervenient**. The orb is the symbol/favicon. Minimum clear space = orb height on all sides. Keep the wordmark `ink` on light or white on `depth`; don't recolour it in accents.

---

## 16. Quick do / don't

**Do:** generous whitespace · navy (`#0E2841`) default text · additive (screen) overlaps · blend accents in gradients · accessible deep variants for accent text/UI · semantic colour + icon + text · visible focus ring · solid functional surfaces · plain, blameless copy.

**Don't:** pure-black body text · pastel text on white · tile flat accent blocks · multiply complements (mud) · text over busy overlap zones · rely on colour alone · strip focus states · dense dashboards · anxious spinners · hype copy.

---

## 17. Paste-in block for agentic interface generation

```
BRAND: Supervenient — AI brought into the middle of a team's work; a calm, intelligent layer that
helps people work as one. Concept: supervenience — a higher layer emerges from and depends on the
work beneath it, shown through translucent, additive, overlapping colour. Principles: Calm Technology,
progressive disclosure, present-then-recede, one shared source of truth, blameless, no dark patterns.
Distribution ~60% neutral / 30% depth / 10% accent.

FONT: Lexend. Headings Medium(500), letter-spacing -0.025em, sentence case. Body Regular(400),
line-height 1.55, min 16px. Emphasise via weight/size, not colour. No all-caps, no heavy bold.
Scale: Display48 H1:36 H2:28 H3:22 BodyL:18 Body:16 Small:14.

COLOUR — core: canvas #FFFFFF | depth #0E2841 | text(default) #0E2841 | black #000000(reserved)
neutrals: 50 #F6F8FA | 100 #ECEFF3 | 200 #DCE2E9(borders) | 400 #9AA5B3(disabled) |
          600 #5B6675(secondary text) | 900 #0E2841(primary text)
accents DECORATIVE only (gradients/fills/glow, NOT text on white):
          sky #93DAF7(lead) | peach #F3AC89 | mint #A1E9AB | lilac #EAA4E0
accessible accent variants (text/icons/UI on white):
          sky #1668B0 | peach #B45A30 | mint #1E7A3E | lilac #9A4D8E
semantic (separate from brand; always colour+icon+text):
          danger #B3261E/surf #FBEAE8 | warning #8A5A00/surf #FCF3E1 |
          success #1E7A3E/surf #E7F6EC | info #1668B0/surf #E6F3FC
focus ring: #1668B0 light / #93DAF7 dark, 2px solid + 2px offset (always visible).

LAYERING (signature): translucent overlapping fields; overlaps blend ADDITIVELY (screen) toward
light — never multiply accents (mud). GROUND RULE: screen-blending only shows on a DARK/deep surface
(>= depth). On light surfaces do NOT screen — use soft translucent tints (normal blend) or place the
luminous layer over a depth panel. Layers read as strata: content sits above a softer layer that
gives rise to it. Layering lives in imagery/backgrounds/AI-indicator; functional surfaces stay solid.

AI INDICATION: not an avatar or chatbot — show AI as a luminous layer over the underlying work.
Intensity scales: ambient (faint tint/edge) -> active (brighter, gentle motion) -> resolved (quiet
attribution). Surface-aware: glowing screen wash on dark; soft accent tint + edge on light (same
meaning, technique adapts). Everything AI produces is editable/dismissible/reversible; show
uncertainty + sources. Orb = the fullest expression of this layer (hero/loading/brand, on a deep ground).

LAYOUT: spacing 4/8/12/16/24/32/48/64/96; radius 6/10/16/24/pill; diffuse navy-tinted shadows
(no pure black). Generous whitespace, one focal point, 1-2 columns, minimal borders.
Motion 120-240ms, decelerate easing, honour prefers-reduced-motion.

ACCESSIBILITY: WCAG 2.2 AA. Text >=4.5:1 (large/UI >=3:1). Never colour-only meaning. Visible focus.
Touch >=44px. Body >=16px.

VOICE & COPY: calm, clear, plainspoken. Short declarative sentences. Errors blameless and plain.
Empty states invite. en-GB spelling, £, DD/MM/YYYY. No hype, no exclamation marks.
```

---

*Version 0.5 — a deliberately minimal system. Verify all contrast pairs with a checker before launch.*
