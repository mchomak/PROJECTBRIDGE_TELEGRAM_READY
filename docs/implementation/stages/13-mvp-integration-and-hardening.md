# Stage 13 — MVP Integration and Hardening

**Goal:** Verify that the complete ProjectBridge MVP works end to end
locally and is safe enough for controlled testing.

## Read first

- `AGENTS.md`
- `docs/README.md`
- `docs/product/MVP_SCOPE.md`
- `docs/architecture/SYSTEM_ARCHITECTURE.md`
- `docs/api/API_CONTRACT.md`
- `docs/security/ACCESS_CONTROL_AND_SECURITY.md`
- `docs/documents/DOCUMENT_LIFECYCLE.md`
- `docs/operations/LOCAL_DEVELOPMENT.md`
- `docs/OPEN_DECISIONS.md`

## Dependencies

All required MVP stages 00–12. If specification generation is formally
deferred, document that decision and test the remaining MVP without it.

## Scope

### End-to-end workflows

Verify the complete local lifecycle:

1.  Register executor and customer accounts.
2.  Verify email addresses.
3.  Create a project and passport as executor.
4.  Invite the customer by email-bound invitation.
5.  Accept invitation using the matching verified email.
6.  Complete the customer questionnaire.
7.  Confirm deterministic passport updates and conflict handling.
8.  Read and manage Project State according to role.
9.  Exchange messages in real time.
10. Upload and access shared documents.
11. Archive, restore, and request permanent deletion according to the
    approved mutual-consent lifecycle.
12. Process supported document text and retrieve evidence if RAG is in
    MVP scope.
13. Run AI analysis and review/apply proposals if live AI provider
    configuration is available.
14. Generate/edit a specification draft if confirmed in MVP scope.

### Security and reliability

- Audit all project-scoped endpoints for membership and role checks.
- Test WebSocket authorization independently.
- Test cross-project access attempts.
- Test upload limits, file validation, and download authorization.
- Verify no AI analyses or pending proposals leak to customer responses.
- Verify all documents remain shared.
- Verify background tasks are retry-safe.
- Verify tasks are enqueued after transaction commit.
- Verify database and file volumes survive restarts.
- Verify no secrets are committed or exposed to the frontend.
- Add request IDs and safe error responses.
- Check logs for secrets and unnecessary document content.

### Quality and documentation

- Run backend test suite.
- Run frontend tests, lint, type checking, and production build.
- Run migrations on a clean database.
- Regenerate OpenAPI and frontend API types.
- Verify Docker Compose startup from documented instructions.
- Update technical docs for implementation deviations approved by the
  product owner.
- Document known limitations and unresolved non-blocking decisions.

## Out of scope

- Public production deployment.
- Production email provider.
- Public object storage migration.
- Full legal/compliance rollout.
- Advanced monitoring platform.
- Mobile applications.

These belong to a later production-readiness phase. Do not present a
local MVP as ready for public customer onboarding while required privacy
and external-AI disclosures remain unresolved.

## Deliverables

- End-to-end test suite or documented test scenarios.
- Security and permission test report.
- Clean local setup instructions.
- Updated OpenAPI and generated types.
- Known limitations and production-readiness checklist.
- Final MVP verification report.

## Acceptance criteria

- [ ] All in-scope MVP workflows complete locally without manual
  database edits.
- [ ] Data persists across normal container restarts.
- [ ] Backend and frontend checks pass.
- [ ] Clean migrations succeed.
- [ ] Project membership and role boundaries are enforced on REST and
  WebSocket.
- [ ] Customer cannot access AI analyses or pending proposals.
- [ ] Both participants see the same shared documents and Project State.
- [ ] AI proposals cannot mutate shared state without executor approval.
- [ ] No project completion percentage is displayed.
- [ ] Document lifecycle matches the finally approved archive-first and
  mutual-consent policy.
- [ ] No secrets are committed or shipped to the browser.
- [ ] Known limitations and deferred production requirements are
  documented.

## Stop conditions

Do not declare MVP complete if any core workflow depends on manual
database edits, if permissions are only enforced in the frontend, or if
a required test was skipped. Report unavailable provider credentials or
unresolved product decisions explicitly.

## Codex handoff

Run Stage 13 as an integration and verification stage. Prefer fixing
defects within the agreed scope; do not add new product features during
hardening.
