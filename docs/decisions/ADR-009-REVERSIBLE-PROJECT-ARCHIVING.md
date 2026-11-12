**ADR-009: Reversible project archiving**

## Context

Project lifecycle includes `draft`, `active`, `completed`, and `archived`. An executor must be able to archive a project and later restore it, while both active participants retain access to its saved data. The approved requirements do not establish automatic deletion or project-retention periods.

## Decision

Archiving is a reversible state transition. When a project enters `archived` from `draft`, `active`, or `completed`, preserve its prior status in `status_before_archive` and set `archived_at`. Preserve the project, memberships, and data. Restore the saved status and clear both archive fields. Do not automatically delete archived projects.

## Why

Hard deletion would prevent the specified restore operation and discard project data. Automatic purging after a presumed period also does not fit: the proposed 12-month project-retention and 14-day backup periods were not approved requirements.

## Consequences

The database and lifecycle services must keep archive status and archive metadata consistent. Archived projects are separated from the ordinary list, remain available in the archive, and can be restored to their exact previous lifecycle status. Retention and deletion policy remain undecided.
