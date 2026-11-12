# ProjectBridge MVP Scope

**Status:** Product baseline  
**Last updated:** 2026-11-11

## 1. Product summary

ProjectBridge is a workspace for managing collaboration between a
project executor and a customer. It consolidates project context,
requirements, communication, documents, tasks, and AI-assisted analysis
into one structured project space.

The MVP must run locally, use a persistent database, and provide working
end-to-end flows rather than static screens.

## 2. Project participants

Each project has two active participant roles:

- **Executor** — creates and manages the project, controls its
  structured state, reviews AI output, and manages the project workflow.
- **Customer** — joins through an email-bound invitation, completes the
  project questionnaire, communicates with the executor, uploads
  documents, and views the shared project state.

The MVP model supports one active executor and one active customer per
project. A user may participate in multiple projects and may have
different roles in different projects.

## 3. MVP capabilities

### 3.1 Accounts and access

- Email-based registration and authentication.
- Email ownership verification.
- Session-based browser authentication.
- Project membership and role-based authorization.
- Invitation links bound to a specific email address.

### 3.2 Project setup

- Create, view, edit, complete, and archive projects.
- New projects start as `draft`; accepting a customer invitation moves a
  draft project to `active`.
- The executor can complete an active project, reopen a completed
  project, archive a draft/active/completed project, and restore an
  archived project to its previous status.
- Completed and archived projects remain readable by both participants.
  Archived projects are shown separately from the main project list.
- Archiving preserves the project and its documents; completed and
  archived project data is not automatically deleted.
- Support four initial project types:
  - `website`
  - `telegram_bot`
  - `automation`
  - `other`
- Create a project passport when a project is created.
- Maintain project context in structured fields.

### 3.3 Customer questionnaire

- Questionnaire definitions are maintained by the product team as
  versioned JSON files in the backend repository.
- Questionnaire branching is deterministic and based on predefined
  rules.
- AI does not generate questionnaire questions or branching rules.
- The questionnaire is selected by project type.
- Existing passport data may prefill questionnaire answers.
- Customer answers are stored separately from the passport.
- On submission, deterministic mapping rules update non-conflicting
  passport fields.
- Conflicting values are preserved and recorded for executor review.
- A submitted questionnaire is locked. The executor may request
  corrections; the customer can then correct and resubmit according to
  the final revision workflow.

### 3.4 Project State

Project State is a composed view of structured project entities:

- stages;
- requirements;
- open questions;
- conflicts;
- tasks.

The customer can view all Project State information. The executor
controls creation and modification of structured Project State records.

Do not calculate or display a completion percentage in the MVP. The
product has no agreed objective weighting model for such a metric.

### 3.5 Communication

- Project chat between the executor and customer.
- REST API for message history and message submission.
- WebSocket for real-time delivery.
- Messages are persisted in PostgreSQL.

### 3.6 Documents

- Both participants can upload documents.
- All project documents are visible to both participants. Private
  documents do not exist in the MVP.
- Maximum upload size: 20 MB per file.
- Supported formats: PDF, DOCX, TXT, and Markdown.
- Text extraction only.
- OCR, audio processing, and video processing are excluded.
- Documents are processed asynchronously and can be used by RAG.
- Archiving and permanent deletion require consent from both project
  participants.

### 3.7 AI assistance

- AI analysis of project context.
- Detection of missing information and potential contradictions.
- AI proposals for changes to Project State.
- Evidence references for AI proposals.
- Executor review is required before an AI proposal changes Project
  State.
- AI must not decide which side of a contradiction is correct.
- Different providers and models can be configured independently for
  each AI task.
- AI analysis and proposals are private to the executor.

### 3.8 Specification

The MVP architecture retains a specification entity and the ability to
generate and edit a specification draft, subject to final confirmation
of the exact generation scope and output format.

Formal customer approval, electronic signing, approval workflows, and
specification comments are deferred.

## 4. Product rules

1.  The customer sees all shared project data except internal AI
    analyses and AI proposals.
2.  The customer can read Project State but cannot directly create or
    modify its structured entities.
3.  Both participants can read and upload project documents.
4.  There are no private project documents.
5.  AI proposals do not update Project State until accepted by the
    executor.
6.  Contradictions must preserve both source values and their
    provenance.
7.  The system does not display an unsupported project completion
    percentage.
8.  Project type identifiers are stable machine-readable values; labels
    may change independently.
9.  Public freelance-order import is not part of the MVP.
10. Consent and disclosure flows for external AI processing are deferred
    from the MVP implementation, but must be reviewed before public
    production use.
11. Completed and archived projects are read-only, subject to the
    executor-only reopen, archive, and restore transitions in the
    lifecycle contract.
12. The MVP does not automatically delete completed or archived
    projects. The previously proposed 12-month project-retention and
    14-day backup periods are not approved product requirements.

## 5. Explicitly deferred

- Importing public orders from freelance marketplaces.
- OCR and image-based text extraction.
- Audio transcription and video processing.
- Private documents.
- Customer access to AI analysis or AI proposals.
- Customer editing of structured Project State.
- Formal specification approval, comments, and electronic signatures.
- Advanced project progress percentages.
- Mobile applications.
- Microservice architecture.
- User-facing AI provider/model configuration.
- External integrations not required for the agreed MVP.
- Consent and external-AI disclosure flows. These remain a
  production-readiness/legal work item.

## 6. MVP acceptance direction

The MVP is functionally ready when the agreed project lifecycle can be
completed locally:

1.  Register and verify users.
2.  Create a project as executor.
3.  Invite a customer by email-bound link.
4.  Accept the invitation with the matching verified email.
5.  Complete the project passport and customer questionnaire.
6.  Preserve questionnaire answers and handle conflicts without silent
    overwrites.
7.  Exchange messages in real time.
8.  Upload, process, view, archive, restore, and mutually delete
    documents.
9.  View and manage Project State according to role permissions.
10. Run AI analysis, review evidence-backed proposals, and apply
    accepted proposals.
11. Generate and edit a specification draft if included in the finalized
    MVP product checklist.

Detailed test scenarios and exact acceptance thresholds remain to be
defined.
