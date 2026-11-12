# Plan - ProjectBridge stages 04-08

**Tier:** T3. **Tickets:** 10. **Waves:** 10 sequential waves.

The work contains five independent product subsystems, each with its own data and integration boundary. Two end-to-end stories per subsystem keep invitations, questionnaire submission, Project State visibility, chat live delivery, and document lifecycle independently reviewable while retaining the required stage commit boundary. All stories are serialized because each follows the prior user workflow and the requested stage order; there is no safe parallel wave.

## Ticket order

| Ticket | Outcome | Requirements | Blocked by | Wave |
|---|---|---|---|---|
| T01 | Issue and manage project invitations | R01, R02, R05, R10, R12, R14, R15, R20, R100i, R101i, R102i | none | 1 |
| T02 | Preview and accept project invitations | R03, R04, R06, R07, R08, R09, R11, R13, R16, R17, R18, R19, R21, R100i, R101i, R102i | T01 | 2 |
| T03 | Build deterministic questionnaire schemas and drafts | R22, R23, R24, R25, R33, R34, R35, R39, R100i, R101i, R102i | T02 | 3 |
| T04 | Submit questionnaires and resolve mappings, conflicts, and corrections | R26, R27, R28, R29, R30, R31, R32, R36, R37, R38, R40, R100i, R101i, R102i | T03 | 4 |
| T05 | Create and edit Project State records | R48, R50, R52, R54, R57, R58, R100i, R101i, R102i | T04 | 5 |
| T06 | Expose shared Project State with evidence and conflict resolution | R41, R42, R43, R44, R45, R46, R47, R49, R51, R53, R55, R56, R100i, R101i, R102i | T05 | 6 |
| T07 | Persist chat messages and provide REST history and sending | R45, R59, R60, R61, R64, R68, R69, R100i, R101i, R102i | T06 | 7 |
| T08 | Deliver chat events over authenticated WebSockets | R62, R63, R65, R66, R67, R100i, R101i, R102i | T07 | 8 |
| T09 | Upload, list, and download shared project documents | R76, R77, R78, R79, R80, R81, R87, R88, R89, R90, R91, R93, R94, R95, R100i, R101i, R102i | T08 | 9 |
| T10 | Run the two-party archive, restore, and deletion lifecycle | R82, R83, R84, R85, R86, R87, R92, R96, R97, R98, R100i, R101i, R102i | T09 | 10 |

## Stage boundaries

- Stage 04: T01-T02. Run Stage 04 acceptance checks, commit each reviewed ticket on `main`; after the stage acceptance checks, immediately attempt the configured upstream push. **Complete locally:** commits `f427226` and `a011ffb`; `git push` failed with `fatal: No configured push destination.` because no remote is configured.
- Stage 05: T03-T04. Run Stage 05 acceptance checks, commit each reviewed ticket on `main`; after the stage acceptance checks, immediately attempt the configured upstream push. **Complete locally:** commits `ea20ae1` and `e50dcb2`; `git push` failed with `fatal: No configured push destination.` because no remote is configured.
- Stage 06: T05-T06. Run Stage 06 acceptance checks, commit each reviewed ticket on `main`; after the stage acceptance checks, immediately attempt the configured upstream push. **Complete locally:** commits `0009b3f` and `ce6c3b5`; `git push` failed with `fatal: No configured push destination.` because no remote is configured.
- Stage 07: T07-T08. Run Stage 07 acceptance checks, commit each reviewed ticket on `main`; after the stage acceptance checks, immediately attempt the configured upstream push.
- Stage 08: T09-T10. Run Stage 08 acceptance checks, commit each reviewed ticket on `main`; after the stage acceptance checks, immediately attempt the configured upstream push.
- If push fails because this checkout has no configured remote, record the exact command/result, retain the local commit, and continue to the next stage. Do not add or guess a remote URL.

## Ticket commit rule

Each ticket is reviewed, green, and committed in its own focused commit. After both tickets and the stage acceptance checks finish, push that stage's commits to `main`. Use path-limited staging/commit so pre-existing unrelated index/worktree changes remain untouched. Update this plan only if implementation evidence forces a recut; record why before changing a wave.

## Cross-cutting requirements

R100i, R101i, and R102i are explicit acceptance requirements on each ticket: authenticated UI and API completion, recoverable failure states, and REST as source of truth. R70-R75 and R99 remain deferred to the reasons in the spec.
