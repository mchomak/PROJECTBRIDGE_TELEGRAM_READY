# ADR-019: Durable Background Dispatch Recovery

**Status:** Accepted for the local MVP
**Date:** 2026-11-13

## Context

Domain requests are committed to PostgreSQL before Celery is published, as
required to prevent workers from observing uncommitted data. The broker publish
runs in an `on_commit` callback, leaving a process-crash window after commit
and before publish. A broker outage can also reject the publish. Without
recovery, AI analysis requests and document uploads can remain queued forever;
a lost document worker can leave processing status stuck. Specification
generation already has a bounded Beat recovery sweep.

## Decision

- Keep durable queue state in each owning app's PostgreSQL model. Do not add a
  cross-domain outbox service or move domain rules into Celery wrappers.
- Retain `on_commit` for the first publish. Use Celery Beat every 60 seconds to
  find stale AI analysis, document-processing, and specification requests.
- Lock each candidate row before reserving dispatch. Reuse the durable request
  or document ID and record a two-minute dispatch lease. Do not reserve another
  publish while its lease is active.
- Consider queued rows stale after one minute. A publish exception is
  ambiguous because the broker may have accepted the message before the
  connection error reached the publisher. Count dispatch exceptions separately
  from reservations, cap the stored exception count at 12, retry with
  exponential backoff from 30 seconds to 30 minutes, and expose
  `queue_unavailable` after five exceptions while leaving
  the operation queued. Continue automatic recovery with the same task ID and
  generation until worker claim or explicit cancellation; neither an exception
  count nor publish attempts fence a possible FIFO backlog. A reservation that
  expires without a recorded exception is also ambiguous. Bound each recovery
  sweep to 100 records.
- Give document execution a six-minute lease, longer than its four-minute hard
  task limit. Requeue expired or legacy processing rows with no lease. Include
  the current processing generation in the task payload and task ID. A stale
  task cannot claim a newer generation, and result writes remain fenced by the
  generation checked in PostgreSQL.
- Treat post-commit broker errors as dispatch failures, not transaction
  failures. In particular, keep the committed document row and media file when
  task publication fails; storage cleanup applies only when the upload
  transaction itself fails.

## Consequences

- Delivery is at least once. Duplicate task messages may exist, but row locks,
  stable dispatch tokens, execution leases, idempotency keys, and generation
  fencing prevent duplicate shared results or stale document output. Dispatch
  retries do not advance a document or execution generation; worker claim does.
- After five dispatch exceptions, `queue_unavailable` is visible while the
  durable request remains queued. Backoff limits retry frequency, and automatic
  recovery continues without manual database intervention. A possibly accepted
  message remains valid and is recovered automatically until worker claim,
  including when older duplicates are already waiting in FIFO order.
- After five dispatch reservations without a worker claim, expose the
  nonterminal `worker_backlog` warning, including when publishes returned
  successfully but no worker has claimed the stable task. Worker claim clears
  either dispatch warning. User-facing copy describes work as waiting for
  processing and continuing to retry; it does not infer acceptance from an
  ambiguous publish exception.
- A provider task may be repeated after a worker crash around an external API
  call. Database fencing prevents stale publication but cannot make paid
  provider calls exactly once.
- PostgreSQL remains the source of truth; Redis remains the task broker. This
  exposes stable dispatch warning codes through the existing AI/specification
  `error_code` fields and document `processing_dispatch_error_code` response
  field; generated OpenAPI TypeScript types must stay current.
