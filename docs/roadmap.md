# Roadmap

This roadmap turns the current prototype into a plan that another engineer or team could execute in phases.

## Phase 1: Align The Repo Around The Current Implementation

Goal: remove confusion between the product narrative and the shipped code.

- Keep the new `docs/` folder as the engineering source of truth.
- Update the root `README.md`, `frontend/README.md`, and `.env.example` so they do not describe missing components as if they already exist.
- Consolidate setup instructions around one supported local path.
- Decide which prototype-only files should remain committed and which local SQLite artifacts should be ignored.

Exit criteria:

- a new contributor can clone the repo and get the stack running from the docs alone
- config names are consistent across code and examples

## Phase 2: Harden The Backend

Goal: make the API and data model safer to extend.

- Introduce a formal migration workflow and stop relying on runtime SQLite schema patching.
- Separate startup seeding from normal app boot where possible.
- Split route handlers from reusable service-layer functions more cleanly, especially for trigger processing.
- Normalize or otherwise formalize serialized fields such as `coverage_types` and `behavioral_signals` if richer querying is needed.
- Add stronger validation and better error contracts for overlapping claim and payout endpoints.

Exit criteria:

- schema changes are applied through migrations only
- trigger logic is reusable without calling route handlers directly
- API contracts are stable enough for frontend and integration tests

## Phase 3: Replace Prototype Integrations

Goal: move from mock behavior to externally integrated behavior.

- Introduce provider interfaces for weather, AQI, traffic, and payments.
- Replace in-process mocks with environment-specific adapters.
- Add a real payout integration strategy or a more explicit simulation boundary.
- Expand admin capabilities to review claims, inspect audit logs, and manage flagged riders.
- Add policy renewal and billing rules if the product is meant to persist beyond weekly demos.

Exit criteria:

- environmental data is sourced from configured providers
- payout processing has a defined external integration or a clearly bounded simulation mode
- admin workflows cover operational review, not just read-only dashboards

## Phase 4: Production-Grade Runtime And Security

Goal: make the system deployable beyond hackathon conditions.

- Move trigger monitoring into a separate worker, scheduler, or queue-backed job system.
- Replace browser `localStorage` token storage with a safer session strategy.
- Add environment-aware secrets management, HTTPS, structured logs, metrics, and alerting.
- Create CI pipelines for backend tests, frontend lint, docs checks, and deployment verification.
- Add role-audited admin actions and stronger authentication guardrails.

Exit criteria:

- API and background work can scale independently
- auth and secret handling meet baseline production expectations
- regressions are gated by automated checks

## Phase 5: Product Expansion

Goal: grow the product beyond the current Bangalore rider demo.

- Expand zone management and expose the full configured zone set in the UI.
- Add multi-trigger simulation tools and richer rider event histories.
- Add policy lifecycle actions such as renewal, pause, and cancellation.
- Add analytics for zone loss ratio, trigger frequency, and rider-level claim behavior.
- Revisit LLM features once the core operational data is trustworthy and stable.

Exit criteria:

- the UI and backend support richer operational scenarios without code-only workarounds
- reporting and analytics support product and underwriting decisions

## Cross-Cutting Priorities

- Preserve a clear separation between prototype-only behavior and production-intended behavior.
- Keep docs updated whenever schema, routes, or setup flows change.
- Prefer explicit contracts over magic startup behavior.
- Add tests at the same time as business-rule changes, especially for triggers, URTS, and payout caps.
