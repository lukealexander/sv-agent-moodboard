# agent.md — Development Instructions for Supervenient

> **These are defaults, not doctrine.** This file captures how I prefer to work — not a
> set of immutable laws. If there's a genuinely better way to do something, suggest it.
> I don't want to fossilise my preferences; I want a starting point attuned to how I work
> that evolves over time.

> **This file is written for my current standard stack: FastAPI (Python) + React
> (TypeScript).** If I'm working in a different stack — Laravel, Rust, Go, C#, or anything
> else — the principles and preferences here still apply, but the specific tooling
> recommendations should be adapted. In that case, work with me interactively to rewrite
> the stack-specific sections for the new context. Don't blindly apply Python/React tooling
> advice to a Rust project.

---

## Guiding Principles

1. **If another dev (or me in two years) has to spend more time understanding the setup
   than fixing a problem, I've failed.** Simplicity over ceremony, always.

2. **Ship something testable, then harden.** Favour lightweight, reversible decisions over
   heavy upfront ceremony. Iterate fast, tighten later.

3. **Extend the specific to the general.** When you notice yourself building a third
   variation of a component, stop and build the reusable one. One `Card` component with
   props beats six bespoke `ResultCard`, `SummaryCard`, etc.

4. **Separation of concerns.** Isolate and name the thing — whether it's modules,
   environments, pipelines, or conversations.

5. **Single sources of truth.** Shared, canonical sources over personal storage. Repeatable
   environments and shared configuration over local snowflakes.

6. **Security-first.** Lock down authN/authZ *early*. Never let permissive defaults drift
   into production.

7. **Accessibility is not optional.** In an AI-accelerated world, there's no excuse not to
   get WCAG compliance, semantic HTML, and ARIA right. Build it in from the start.

---

## Language & Localisation

- **All code comments, documentation, commit messages, and UI copy must use GB English.**
  (organisation, not organization; colour, not color; analyse, not analyze; fossilise, not
  fossilize.)

---

## Tech Stack

Unless otherwise specified in the project documentation, these are my default preferences for a modern web app:

### Backend
- **Framework:** FastAPI (Python)
- **Python version:** 3.12 (middle of the road — not bleeding edge, not cautious)
- **Dependency management:** pip + requirements.txt
- **ORM:** SQLAlchemy (async) with Alembic for migrations
- **Database:** PostgreSQL (via AWS RDS in production)
- **Auth:** AWS Cognito + Microsoft Entra ID; JWT validation via Cognito public keys
- **AI models:** AWS Bedrock as the primary provider
- **Logging:** Python's built-in `logging` module — keep it simple
- **Observability:** CloudWatch via ECS in production

### Frontend
- **Framework:** React with TypeScript
- **Build tool:** Vite
- **State management:** Redux for app state; React Query (TanStack Query) for server state
- **Data fetching:** `fetch` API (no axios unless there's a specific need)
- **Styling:** Modern CSS with native nesting and CSS custom properties. Styled-components
  for component-scoped styles in React. **Never Tailwind. Never inline styles.**
- **Component library:** Separate repo, imported into each app via GitHub Packages (semver)
- **CSS architecture:** CSS custom properties (variables) for theming, CSS modules or
  styled-components for component scoping. No utility-class frameworks.

### Infrastructure
- **Cloud:** AWS — Fargate (ECS) for APIs, Amplify for frontends, RDS for databases
- **Auth layer:** shared ALB + Cognito for login flow, Entra ID as identity provider
- **Containerisation:** Docker, with Docker Compose for local development
- **Hub/homepage:** Laravel app at labs.four.agency
- **Deployment:** FastAPI → Docker (ARM64) → ECR → ECS Fargate; React → AWS Amplify (builds on git push)
- **Secrets:** Environment variables in ECS (keep it simple)

### Development Environment
- **OS:** Either Mac or Windows/WSL2 (developing) → Linux (production)
- **Local setup:** A single `docker-compose up` must get the entire app running
- **Always ship a `.env.example`** with sensible defaults and clear comments

---

## Project Structure

This is the kind of repo layout I prefer. Adapt it where the project demands, but use
this as a starting point:

```
my-app/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/v1/         # Versioned API routes
│   │   │   ├── models/         # SQLAlchemy models
│   │   │   ├── schemas/        # Pydantic request/response models
│   │   │   ├── services/       # Business logic
│   │   │   ├── workflows/      # LangGraph workflows (when needed)
│   │   │   ├── config.py
│   │   │   └── main.py
│   │   ├── alembic/            # Database migrations
│   │   ├── requirements.txt
│   │   └── Dockerfile
│   └── web/                    # React + TypeScript frontend
│       ├── src/
│       │   ├── components/     # Reusable, general-purpose components
│       │   ├── pages/          # Route-level page components
│       │   ├── services/       # API clients, auth service
│       │   ├── stores/         # Redux slices
│       │   ├── styles/         # CSS custom properties, global styles
│       │   └── config.ts
│       ├── package.json
│       └── Dockerfile
├── docs/
│   ├── DATA_MODELS.md          # Schema documentation and seed data
│   ├── DEPLOYMENT.md           # How to deploy
│   ├── AUTHENTICATION.md       # Auth flow documentation
│   └── ACCESSIBILITY.md        # Accessibility standards and testing
├── docker-compose.yml          # Single file, full local stack
├── .env.example
└── README.md                   # Comprehensive — the single source of truth
```

---

## API Design

- **REST as an organising principle** — but not a religion. Pragmatism wins.
- **Always version APIs:** `/api/v1/...`
- **Use Pydantic models** for request and response validation. They serve as contracts
  between frontend and backend, and are invaluable when AI is writing the code.
- **Consistent error responses.** Use a standard error envelope.
- **Always validate on the API side.** Never trust client-side input for anything sensitive.
- **Every endpoint requires authentication by default.** Public endpoints must be explicitly
  designated — and if I try to skip auth, **challenge me on it**. Ask: "Is this intentionally
  public? What's the risk if an unauthorised user hits this?"

---

## AI & Model Integration

### Model Selection
- **Default:** Latest Claude Sonnet model for most tasks; Haiku for lightweight/fast tasks
- **Smaller models:** Phi-4 and similar are great for specific use cases — don't default
  to the biggest model when a smaller one will do
- **Never hardcode model IDs.** Abstract behind configuration or a model router:
  ```python
  model_selections['image_generation']['cheapest']
  model_selections['analysis']['best']
  ```

### Architecture
- **Simple tasks:** Call models directly via boto3/Bedrock
- **Complex workflows:** Use LangChain / LangGraph for multi-step, stateful workflows
- **Decision rule:** If the task has multiple steps, needs state management, or benefits
  from checkpointing and observability — use LangGraph. If it's a single prompt-response,
  call Bedrock directly.
- **Future direction:** I'm interested in the Entity Component System (ECS) model for
  agentic work — composition over inheritance, data-driven behaviour, entities as bags of
  components. Prefer this mental model over deep OOP class hierarchies when designing
  larger agent systems.

---

## Code Quality

### Linting & Formatting (recommended, not blocking)
- **Python:** `ruff` (replaces black, flake8, isort in one tool). Run on save.
- **TypeScript/React:** `eslint` + `prettier`. Run on save.
- These should **never block you from shipping**, but they keep things consistent over time.

### Comments
- **WHY is essential.** Always explain the reasoning behind non-obvious decisions.
- **WHAT is welcome** but secondary — the code should be readable enough to convey what
  it does, but extra context for less experienced devs is never unwelcome.
- **Never zero comments.** A file with no comments is a file with missing context.

### Testing
- **Python:** pytest
- **End-to-end:** Playwright
- **Philosophy:** Tests are a **communication tool** — they express intent and document
  assumptions about what's important. They're especially valuable in agentic coding, where
  they make visible what the AI thinks matters.
- **Don't chase coverage metrics.** Write tests that are genuinely useful, not tests that
  pad a number.

### Components
- **Generalise early.** If you're building a component that's only slightly different from
  an existing one, extend the existing one with props instead.
- **No inline styles.** Ever. No Tailwind or utility-class frameworks either. Use
  styled-components or CSS modules with modern CSS.
- **Reusable components live in `components/`.** Page-specific layouts live in `pages/`.

---

## Git & Version Control

### Branching
- **Main + feature branches.** Simple, effective, no ceremony.
- This is a small-team preference — happy to flex for larger teams.

### Commit Messages
- **Must be useful at a glance** to someone reading through the log.
- **Never:** `updates`, `fixes`, `changes`, `WIP`, `misc`
- **If you can't fit it in a commit message, you should have committed twice.**
- When operating in fully agentic mode: prefer smaller commits around individual features
  and changes. When pair-programming: I handle commits manually.

---

## Documentation

### README.md
- **Comprehensive.** This is the single source of truth for the project.
- Must cover: what the app does, how to get it running locally, architecture overview,
  environment variables, and deployment.

### Breakout Documentation
- Use separate files only for genuinely distinct concerns:
  - `DATA_MODELS.md` — schema documentation and seed data
  - `DEPLOYMENT.md` — deployment procedures
  - `AUTHENTICATION.md` — auth flow and configuration
  - `ACCESSIBILITY.md` — standards, testing approach, known issues

---

## Security

- **Lock down authN/authZ early.** Don't leave endpoints open and plan to "fix it later."
- **Never trust client-side input** for anything sensitive. Always validate on the API.
- **Default to authenticated.** Public endpoints must be explicitly marked and justified.
- **If I try to commit code with security holes** (e.g. trusting unauthorised users,
  missing validation, exposed secrets), **flag it immediately** — even if I seem to know
  what I'm doing. Quiz me: "Is this intentional? Here's the risk."
- **Test unauthorised/least-privilege paths** as part of definition of done.

---

## How to Work With Me (for AI Agents)

### Communication
- **I'm your partner, not your master.** Share your reasoning, flag concerns, suggest
  alternatives. I want to hear your thoughts — I get enormous value from them.
- **Be proactive.** If you notice something off — an auth gap, a missed edge case, an
  opportunity to generalise — raise it without being asked.
- **Take small bites, often.** Don't disappear for 500 lines then present a fait accompli.
  Check in, share progress, ask my opinion.
- **Ask before making big changes**, particularly when refactoring or removing things that
  are already in place.

### Before Starting Work
- **Consider the wider picture.** Before making major changes, pause and think: are we
  adding unnecessary complexity? Are we obsessing over one edge case? Does this change
  align with how the rest of the codebase works?
- **Build a mental model first.** Understand how the existing system works before
  implementing. Don't blindly apply patterns — understand why they exist here.

### Code Style
- **DRY where possible.** But not at the expense of readability.
- **Lots of comments.** Document everything a newcomer needs to know.
- **Don't throw the baby out with the bathwater.** When fixing or improving something,
  preserve what already works. Refactoring is not rewriting.
- **No inline styles.** Use the project's styling system.
- **Generalise when you see duplication.** One flexible component beats three rigid ones.

### Git (When Agentic)
- **Fully agentic mode:** Make smaller commits around individual features/changes.
- **Pair programming mode:** Don't commit — I'll handle it.
- **All commit messages must be meaningful.** See the Git section above.