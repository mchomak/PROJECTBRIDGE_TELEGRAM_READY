# ProjectBridge — Development Roadmap

**Status:** Proposed implementation sequence based on the accepted MVP
and architecture documents  
**Last updated:** 2026-11-11

## 1. Delivery strategy

Build ProjectBridge as a sequence of independently reviewable vertical
slices. Each stage should leave the repository in a runnable state and
deliver a coherent capability across the database, backend, frontend,
and tests where applicable.

Do not build the entire backend first and postpone all frontend
integration until the end. Implement and verify each user-facing
workflow end to end.

The plan contains 14 stages:

| Stage | Name                                   | Main outcome                                                           |
|------:|----------------------------------------|------------------------------------------------------------------------|
|    00 | Repository baseline and tooling        | Clean monorepo and development conventions                             |
|    01 | Application skeleton and local runtime | Frontend, backend, PostgreSQL, Redis, Celery, Channels run locally     |
|    02 | Accounts and authentication            | Registration, login, sessions, email verification                      |
|    03 | Projects and passport                  | Create and manage projects and project passports                       |
|    04 | Email-bound invitations                | Invite a customer and securely add them to a project                   |
|    05 | Questionnaire                          | Versioned questionnaire, saved answers, deterministic passport mapping |
|    06 | Project State                          | Shared stages, requirements, tasks, questions, and conflicts           |
|    07 | Chat                                   | Persisted project chat with real-time delivery                         |
|    08 | Document management and lifecycle      | Shared uploads, downloads, archive and deletion consent workflows      |
|    09 | Text processing and RAG                | Extract text, chunk documents, create embeddings, retrieve evidence    |
|    10 | AI provider routing                    | Provider adapters and independently configurable task profiles         |
|    11 | AI analysis and proposals              | Evidence-backed analysis, contradiction proposals, executor review     |
|    12 | Specification                          | Generate and edit a specification draft                                |
|    13 | MVP integration and hardening          | End-to-end acceptance, security, reliability, local MVP sign-off       |

Each stage has an individual implementation brief in
`docs/implementation/stages/`. Give Codex one stage brief at a time.

## 2. Before coding: documentation alignment gates

The technical documentation is the implementation baseline, but several
items must be resolved before the affected stage starts. Do not let
Codex invent answers.

### 2.1 Document deletion sequence

The product decision discussed earlier was that a document must first be
moved to an archive, become hidden from the active list, remain
restorable, and only then be eligible for permanent deletion with both
participants’ consent.

The current `docs/documents/DOCUMENT_LIFECYCLE.md` and
`docs/api/API_CONTRACT.md` describe a direct `deletion_pending` flow
that does not explicitly require the document to have been archived
first.

**Action before Stage 08:** reconcile the product rule, lifecycle state
machine, database model, and API contract. Codex must not implement the
conflicting interpretations.

### 2.2 Retention and deletion grace period

The technical documents contain a 30-day cancellation window for
permanent deletion, 12-month retention for completed projects, and
14-day backup retention. These are implementation baselines in the
documents, but they were not separately confirmed in the product
discussion.

**Action before implementing scheduled deletion/retention:** confirm
these periods or update the documents. Do not hard-code unconfirmed
policy values.

### 2.3 Questionnaire rules

Before Stage 05, define: - exact question sets and branching for all
four project types; - schema versioning rules; - exact
answer-to-passport mapping; - correction/resubmission behavior; - where
deterministic questionnaire conflicts are visible and how they are
resolved.

Relevant open decisions: `docs/OPEN_DECISIONS.md` items 1–3 and 19.

### 2.4 Project State workflow

Before Stage 06, confirm statuses and allowed transitions for stages,
requirements, tasks, open questions, and conflicts. See
`docs/OPEN_DECISIONS.md` item 5.

### 2.5 RAG and AI configuration

Before embedding migrations and real provider integration, choose: -
initial embedding model and vector dimension; - chunking and retrieval
parameters; - providers and model identifiers per AI task; - compatible
fallback behavior.

See `docs/OPEN_DECISIONS.md` items 10–18 and 26.

### 2.6 Specification scope

Before Stage 12, confirm generation inputs, output format, and whether
specification generation is mandatory for MVP acceptance. Formal
customer approval remains out of scope. See `docs/OPEN_DECISIONS.md`
item 7.

## 3. Stage sequence and dependencies

``` text
00 Repository baseline
        |
01 Local runtime and application skeleton
        |
02 Accounts and authentication
        |
03 Projects and passport
        |
04 Email-bound invitations
        |
05 Questionnaire
        |
06 Project State
        |-------------------|
        |                   |
07 Chat              08 Documents
                            |
                     09 Text processing + RAG
                            |
                     10 AI provider routing
                            |
                     11 AI analysis + proposals
                            |
                     12 Specification
                            |
                     13 MVP integration and hardening
```

Stages 07 and 08 can be developed in parallel only after Stage 06 is
stable and the team agrees on separate ownership. The recommended
default is sequential execution to keep reviews and migrations simple.

## 4. Common definition of done

Every stage must satisfy all applicable criteria:

1.  Scope matches its stage brief; no future-stage features are
    included.
2.  Database changes are implemented as migrations and work on a clean
    database.
3.  Backend validation and permissions are enforced server-side.
4.  Frontend behavior follows the FSD structure and uses the documented
    API.
5.  Tests cover successful behavior, invalid input, permissions, and
    relevant failure paths.
6.  API changes are reflected in OpenAPI and generated frontend types.
7.  Background tasks are retry-safe and are scheduled after transaction
    commit.
8.  Documentation is updated if implementation changes a contract or
    decision.
9.  Relevant test, lint, type-check, and build commands pass.
10. The stage is committed as one coherent unit and reviewed against its
    acceptance criteria.

A stage must not be marked complete if a required check was skipped or a
blocking product decision remains unresolved.

## 5. Stage briefs

### Stage 00 — Repository baseline and tooling

Establish the monorepo layout, preserve existing work, configure
development tooling, environment templates, and repository scripts.

Brief: `stages/00-repository-baseline-and-tooling.md`

### Stage 01 — Application skeleton and local runtime

Create the minimal React/Vite and Django/DRF applications and run them
with PostgreSQL, Redis, Celery, and Channels through Docker Compose.

Brief: `stages/01-application-skeleton-and-local-runtime.md`

### Stage 02 — Accounts and authentication

Implement the custom email-based user model, registration, login/logout,
sessions, CSRF, and email verification.

Brief: `stages/02-accounts-and-authentication.md`

### Stage 03 — Projects and passport

Implement project creation, membership, the four project types, passport
persistence, versioning, and project screens.

Brief: `stages/03-projects-and-passport.md`

### Stage 04 — Email-bound invitations

Implement invitation creation, delivery, preview, expiry/revocation, and
acceptance by the matching verified email.

Brief: `stages/04-email-bound-invitations.md`

### Stage 05 — Questionnaire

Implement deterministic, versioned questionnaire schemas, customer
submissions, separate answer storage, passport mapping, and conflict
handling.

Brief: `stages/05-questionnaire.md`

### Stage 06 — Project State

Implement shared stages, requirements, tasks, open questions, and
conflicts with executor-only mutation.

Brief: `stages/06-project-state.md`

### Stage 07 — Chat

Implement persisted messages, history, idempotent submission, WebSocket
delivery, and the FSD chat interface.

Brief: `stages/07-chat.md`

### Stage 08 — Document management and lifecycle

Implement shared upload/download, validation, archive/restore, and
mutually approved permanent deletion.

Brief: `stages/08-document-management-and-lifecycle.md`

### Stage 09 — Text processing and RAG

Implement asynchronous text extraction, chunking, embeddings, vector
retrieval, and document evidence references.

Brief: `stages/09-text-processing-and-rag.md`

### Stage 10 — AI provider routing

Implement the provider-neutral AI Router, capability interfaces,
provider adapters, and independent profiles for each AI task.

Brief: `stages/10-ai-provider-routing.md`

### Stage 11 — AI analysis and proposals

Implement project analysis, contradiction detection, evidence-backed
proposals, executor review, and safe application to Project State.

Brief: `stages/11-ai-analysis-and-proposals.md`

### Stage 12 — Specification

Implement specification draft generation and executor editing after the
exact output and input contract is confirmed.

Brief: `stages/12-specification.md`

### Stage 13 — MVP integration and hardening

Run complete workflows, close permission gaps, improve error handling
and observability, test persistence and recovery, and sign off the local
MVP.

Brief: `stages/13-mvp-integration-and-hardening.md`

## 6. Work explicitly outside this MVP plan

Do not add these during the stages above unless the product owner
changes scope:

- microservices;
- public freelance-order import;
- OCR;
- audio or video transcription/processing;
- private project documents;
- customer access to AI analyses or proposals;
- customer editing of structured Project State;
- automatic AI mutation of project data;
- project completion percentages;
- formal customer approval/signing of the specification;
- production hosting, public email delivery, and full legal/compliance
  rollout.

A separate production-readiness phase should be planned after the local
MVP is accepted.

## 7. Codex execution procedure

For every stage:

1.  Give Codex the exact stage brief path.
2.  Require it to read `AGENTS.md`, `docs/README.md`, the stage brief,
    and all referenced technical documents.
3.  Ask it to inspect the current repository before editing.
4.  Require a short plan and an explicit list of files/components
    expected to change.
5.  Let it implement only that stage.
6.  Require it to run the acceptance checks and report exact results.
7.  Review the diff and test report. If a separate reviewer is
    available, use the read-only review prompt in `AGENTS.md`.
8.  Merge/commit only after the stage passes.

Recommended prompt:

> Implement Stage `<NN>` from
> `docs/implementation/stages/<stage-file>.md`. Follow `AGENTS.md`. Read
> all referenced documentation and inspect the current repository first.
> Implement only the stated scope, add tests for the acceptance
> criteria, run the required checks, and report changed files, test
> results, and unresolved issues. Stop if the documentation conflicts or
> a required product decision is missing.

## 8. How to update this roadmap

If a stage changes architecture, data contracts, permissions, or product
behavior: - stop and explain the impact; - obtain the product owner’s
decision; - update the relevant technical document; - add or amend an
ADR for non-trivial architecture decisions; - update the affected stage
brief before implementation continues.

Do not treat this roadmap as permission to override the detailed
technical documents or unresolved product decisions.
