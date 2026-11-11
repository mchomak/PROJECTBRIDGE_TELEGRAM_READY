# Backend Architecture

**Status:** Agreed architecture baseline  
**Last updated:** 2026-11-11

## 1. Stack and deployment shape

- Python
- Django
- Django REST Framework
- PostgreSQL
- pgvector
- Redis
- Celery
- Django Channels
- ASGI

The backend is a modular monolith: one deployable application divided
into business-domain Django apps. It is not a collection of
independently deployed microservices.

## 2. Domain modules

| Django app       | Ownership                                                                        |
|:-----------------|:---------------------------------------------------------------------------------|
| `accounts`       | User model, registration, authentication, email verification                     |
| `projects`       | Project, membership, passport, project lifecycle                                 |
| `invitations`    | Email-bound project invitations                                                  |
| `questionnaire`  | Versioned questionnaire submissions and answers                                  |
| `chat`           | Project messages and chat events                                                 |
| `documents`      | File metadata, storage, parsing lifecycle, chunks, embeddings, deletion workflow |
| `project_state`  | Stages, requirements, open questions, conflicts, tasks, evidence                 |
| `ai_assistant`   | AI profiles, provider adapters, routing, analysis runs, proposals                |
| `specifications` | Specification draft and generation orchestration                                 |
| `common`         | Shared infrastructure utilities and audit log where appropriate                  |

A Django app should own its models, migrations, services, selectors,
permissions, API serializers/views, and tests.

## 3. Internal module structure

Recommended structure for a domain app:

``` text
app_name/
├── models.py
├── selectors.py
├── services.py
├── permissions.py
├── api/
│   ├── serializers.py
│   ├── views.py
│   └── urls.py
├── tasks.py
├── tests/
└── apps.py
```

Not every module needs every file. Add files when the module requires
them; avoid empty abstraction layers.

### Models

Define persistent entities, database constraints, and indexes.

### Selectors

Contain read/query operations. They retrieve data and do not perform
business-state transitions.

### Services

Contain business operations and state changes. Services validate
business invariants and use database transactions when an operation
spans multiple records.

### API layer

Views handle HTTP orchestration. Serializers validate and transform
input/output. Permissions enforce authorization. Views should remain
thin and delegate business work to services.

### Tasks

Celery tasks orchestrate long-running or scheduled work. They should
call domain services rather than duplicate domain rules.

## 4. Dependency rules

- A domain module owns its data and state transitions.
- Other modules must not bypass the owning module’s service interface to
  mutate its records.
- Cross-module reads use selectors or explicitly documented query
  interfaces.
- Avoid circular dependencies.
- Shared utilities must remain generic; do not turn `common` into a
  dumping ground for business logic.
- API views are not a cross-module integration mechanism.

## 5. Transactions and asynchronous work

Use database transactions for logically atomic operations, including:

- project creation with membership and passport creation;
- applying an accepted AI proposal to Project State;
- questionnaire submission and deterministic passport updates;
- document lifecycle state transitions and approval recording.

Schedule Celery tasks after the transaction commits so workers do not
read uncommitted data. Tasks must be retry-safe and should use stable
object IDs rather than large serialized model objects.

For critical background events, assess a transactional outbox if
measured reliability requirements exceed the simpler
`transaction.on_commit` approach.

## 6. Why not microservices now

The team is small and part-time, and the MVP has tightly related domains
with frequent cross-domain transactions. Microservices would add network
contracts, distributed failure handling, independent deployments,
observability requirements, and eventual-consistency concerns before
those costs provide meaningful value.

The modular monolith still allows independent runtime processes and
horizontal scaling:

- multiple Django/ASGI instances;
- separate Celery worker pools;
- dedicated queues for AI and document processing;
- independent scaling of workers and web processes.

Extract a domain into a service only when there is a measurable reason,
such as independent scaling, fault isolation, release cadence, security
boundary, or team ownership.

## 7. Authentication

Use Django session authentication for the browser application, with
HttpOnly cookies and CSRF protection. Email verification is required
before a user can accept an email-bound project invitation or use the
authenticated product flow.

## 8. API documentation

Use `drf-spectacular` to generate OpenAPI from the actual API
implementation. The OpenAPI schema is the source for generated frontend
TypeScript types.
