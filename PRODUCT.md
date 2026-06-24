# Product

## Register

product

## Users

Designers and creatives at the **start** of a project, in a divergent, exploratory
headspace. They arrive with a fuzzy sense of direction — a brief, a feeling, a few
reference points — and need to externalise and sharpen it.

- **Context:** kicking off a brand, campaign, product, or creative piece. They want to
  move from a vague intent to a concrete visual direction quickly, without hand-assembling
  a board from scattered tabs and screenshots.
- **Job to be done:** turn an intent they can only half-articulate into a coherent
  moodboard — imagery, palette, type, references — that captures a direction they can
  build on, react to, or share with collaborators and clients.

## Product Purpose

Agent Moodboard is an interface for generating moodboards through a **guided, multi-step
conversation**. Instead of a blank canvas, it asks a sequence of questions that
progressively narrow an open brief into a defined visual direction, then assembles a
moodboard from the answers.

The purpose is **creative discovery**: helping a designer surface, test, and refine a
direction they couldn't have specified up front. Each step should advance their thinking,
not just collect input. Success looks like a designer leaving with a board that feels
*theirs* — accurate to an intent they only half-articulated — and the confidence to act
on it.

Agent Moodboard also serves as the reference agentic microservice on the Supervenient
labs platform, but it is to be designed and built as a **polished, real product** that
stands on its own — never read as a demo or test harness.

## Brand Personality

The Supervenient voice: **confident, clear, quietly intelligent.** Plainspoken — short
declarative sentences, warm but unfussy, human and never corporate. The cleverness is in
the thinking, not the volume.

For a creative-discovery tool this means a **calm collaborator** that asks good questions
and then gets out of the way — never a hype-y "AI magic" pitch, never a chatty persona.
Emotional goal: the unhurried confidence of a good creative partner. en-GB throughout.

## Anti-references

- **Hype and "AI magic" framing** — exclamation marks, manufactured urgency,
  feature-dumping, hard-sell adjectives.
- **AI-as-chatbot / avatar** — a docked corner assistant or named persona. The
  intelligence sits in the middle of the work (Supervenient §7), not in a widget.
- **Generic SaaS dashboard clichés** — hero-metric templates, endless identical
  icon + heading + text card grids, a tiny tracked-uppercase eyebrow over every section.
- **Pinterest-style infinite feeds** — a wall of undifferentiated cards as the primary
  surface. A moodboard is composed and deliberate, not an endless scroll.
- **Dense, anxious, "loud" interfaces.** A bold palette is not a loud interface
  (Calm Technology).

## Design Principles

1. **Discovery over input** — the multi-step questions *are* the product. Each step should
   feel like progress in thinking, not a form to fill in; reveal depth on intent
   (progressive disclosure).
2. **Present, then recede** — surface the agent's contribution when it's useful, then step
   back so the emerging board is the focus.
3. **The board is the hero** — facets, gradients, and the convergence/spark serve the
   moodboard. Chrome never competes with the visual direction being formed.
4. **Editable, reversible, honest** — everything the agent proposes is steerable. Show
   uncertainty, make redirection easy, keep copy blameless. No dark patterns.
5. **Bold but disciplined** — saturated jewel facets on a deep ground, deployed with
   restraint (60-30-10); one focal point per view.

## Accessibility & Inclusion

WCAG 2.2 AA (Supervenient §5.9), verified against a checker before launch.

- Body text ≥ 4.5:1; large / UI text ≥ 3:1. Placeholder text held to the same body
  standard.
- **Never colour alone** — pair meaning with icon and/or text, especially given the
  facet/semantic hue overlap.
- Always-visible focus ring (`#7B4BA8` light / `#2FB6D4` dark, 2px solid + 2px offset).
- Touch targets ≥ 44×44px; body text ≥ 16px.
- Honour `prefers-reduced-motion` — the kaleidoscope's motion stops; reveals fall back to
  crossfade or instant.
- Colour-blind-safe categorical order for any facet-coded content; data always labelled.
