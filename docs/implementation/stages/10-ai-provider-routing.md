# Stage 10 — AI Provider Routing and Model Profiles

**Goal:** Build a provider-neutral AI integration layer that can select
a different provider/model for every AI task.

## Read first

- `AGENTS.md`
- `docs/ai/AI_ARCHITECTURE.md`
- `docs/database/DATA_MODEL.md` — AIModelProfile and AIAnalysisRun
- `docs/architecture/BACKEND_ARCHITECTURE.md`
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/OPEN_DECISIONS.md` items 10, 15, 17, and 18

## Dependencies

Stages 01 and 09 for embedding capability integration. The router
foundation may be developed earlier, but the final embedding profile
depends on Stage 09 decisions.

## Required decisions

Select initial providers and model identifiers for each required task
before enabling real provider calls. Confirm compatible fallback
behavior, timeouts, retries, cost controls, and prompt-version policy.

## Scope

### Core abstraction

- Implement a central AI Router.
- Define stable task keys and typed input/output contracts.
- Define capability interfaces separately for text generation,
  embeddings, and reranking.
- Implement provider adapters behind those interfaces.
- Keep provider SDK imports and provider-specific request/response
  mapping inside adapters.
- Normalize provider errors and usage metadata.

### Task-level profiles

- Implement AIModelProfile configuration.
- Support an independent profile for each task, including:
  - `message_analysis`
  - `conversation_analysis`
  - `contradiction_detection`
  - `document_embedding`
  - `rag_reranking`
  - `specification_generation`
- Allow a task’s provider/model to change without modifying domain
  business logic.
- Validate that the selected provider supports the requested capability.
- Support only compatible fallback profiles.
- Keep credentials in environment configuration or a secret manager,
  never in profile records or frontend code.
- Restrict profile management to backend administration in the MVP.

### Observability

- Record task key, actual provider/model, profile version, prompt
  version, input hash, status, timing, usage, and estimated cost when
  available.
- Do not store full prompts or unnecessary sensitive source content by
  default.

### Testing

- Provide deterministic fake/mock adapters for tests.
- Test profile selection, capability validation, fallback compatibility,
  normalized errors, and usage recording.

## Out of scope

- Customer-facing provider/model settings.
- A generic workflow engine for arbitrary AI tasks.
- Direct provider SDK use from domain apps.
- Hard-coded single-provider business logic.

## Deliverables

- AI Router.
- Capability interfaces.
- Provider adapter interface and selected adapters.
- Task-level model profiles.
- Restricted profile configuration.
- Usage/error metadata.
- Unit and integration tests.

## Acceptance criteria

- [ ] Domain services call the router by task key, not provider SDK.
- [ ] Each task can resolve an independent provider/model profile.
- [ ] Changing one task profile does not require business-logic changes.
- [ ] Unsupported capabilities are rejected before provider execution.
- [ ] Credentials are never stored in profile rows or exposed to the
  frontend.
- [ ] Provider errors are normalized.
- [ ] Analysis metadata records the provider/model actually used.
- [ ] Tests use mock adapters and do not require paid provider calls.
- [ ] Embedding profiles cannot silently mix incompatible vector
  dimensions.

## Stop conditions

Do not select providers/models or fallback behavior without resolving
the corresponding open decisions. If no provider has been selected,
implement and test the abstraction with mock adapters only, then report
that live AI execution remains gated.

## Codex handoff

Implement Stage 10 only. The key acceptance requirement is independent
per-task model routing without provider coupling in business logic.
