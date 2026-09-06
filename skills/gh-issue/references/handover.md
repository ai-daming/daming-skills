# Handover at closure

Use for CLOSE, not as a new gate on every Issue edit. The goal is to prevent known unfinished obligations from disappearing when their source work closes.

## Discover and classify

Read the source body and all comments with pagination. Follow relevant linked design, migration, runbook and review/evidence sections that define remaining work. Do not recursively audit unrelated projects. Record the checked sources/revisions and any unavailable pages or attachments; a failed or partial read of a required source prevents a completeness claim and closure until resolved.

Search terms such as `移交`, `另行`, `后续`, `待办`, `归口`, `follow-up`, `deferred`, `不在本次范围`, `manual`, or `before activation` help find candidates. Also trace prerequisites from the actual delivery contract: no keyword hits does not prove no obligations. Read context, reconcile later completion or superseding decisions, and de-duplicate the same item across comments and documents.

Separate:

- **Current AC:** required to complete the source work; cannot be discharged by a follow-up ticket.
- **Accepted later-gate prerequisite:** belongs to a specified later gate, with safe ordering and a condition that blocks progression until verified. This may permit implementation/merge while still blocking release; apply the source Issue's actual closing contract.
- **Out-of-scope obligation:** real unfinished work requiring a receiving owner and revisit mechanism.
- **Optional idea or non-goal:** no obligation unless an accepted requirement/decision makes it one. A keyword does not turn it into debt; give a brief exclusion reason when it could otherwise be mistaken for an obligation.

## Decide the disposition

| Status | Required evidence |
|---|---|
| Done / 已完成 | A result demonstrating the item's completion criteria, not merely an agent statement or closed checkbox |
| Handed over / 已移交 | All three conditions below, verified at the destination |
| Explicitly declined / 明确不做 | Decision from someone authorized to accept the consequence, recording the reason and risk; merely marking `wontfix` is not enough |
| Unassigned or unverified / 尚未承接 | Missing destination, responsibility, revisit mechanism, or required evidence; keep the source open |

All three are required for a handover:

1. **Findable work:** a stable link to an Issue, task, or step inside an owned release/operations task; it states the remaining scope and what counts as done.
2. **Confirmed responsibility:** a named person or accountable team has accepted it, or an established repository assignment policy clearly gives that recipient responsibility. An unacknowledged arbitrary assignment or “business team will handle it” is insufficient. Explicit self-assignment by the responsible user can count; no extra confirmation ritual is needed.
3. **A real revisit:** it is in a maintained pending-work queue and has a review date or actionable trigger, with someone/process responsible for checking it. A release-blocking checklist or a team's scheduled backlog review can count. A searchable document, an ignored open list, or “someday” alone cannot. Automated alerts are optional.

Recheck stale, cancelled, closed, redirected, or overdue receiving work; it cannot remain “handed over” solely because its old link exists. A completed receiving task can supply completion evidence. An overdue review needs current confirmation and a valid next check, not automatic deletion or fabricated success.

## Record once, then act

Use the source's existing task/closure record, or a concise closure preview:

| Item and source | Governing AC or later gate | Status | Completion or destination evidence | Responsible party and acceptance | Review date/trigger | Missing fact/action |
|---|---|---|---|---|---|---|
| <remaining obligation> | <scope/gate> | <disposition> | <stable evidence link> | <confirmed responsibility> | <actionable check> | <none or specific gap> |

Omit a blank table if complete source inspection found no obligations; state the inspected scope and result. Reference this record in other reports instead of maintaining parallel ledgers.

- If a current AC is unmet, keep the Issue open. To change AC, follow the normal contract-change and authorization process first; transferring the work or accepting a risk is not that process.
- If only out-of-scope obligations remain, verified handover or authorized decline can permit closing the original work under repository policy. They need not all be executed immediately.
- If the user cancels work, use the repository's cancellation/not-planned semantics and record remaining risk/obligations; do not claim delivery completed.
- Before proposing a new Issue, look for an existing destination that covers the work. Prepare concrete updates and request only the missing decision/authorization. Creating an Issue, assigning someone, sending an acceptance request, and closing the source are distinct writes requiring applicable authorization.
- Read back destination writes before CLOSE. If source or receiving evidence changes materially before closing, reassess. Partial success (destination created but source still open) is a real result; do not repeat creation or claim the whole transfer succeeded.

## Calibration

- A required data mapping is only in a migration comment: it remains unassigned; find an owned release task and make its activation gate explicit before claiming handover.
- A receiving Issue has a number but no accepted owner or review trigger: it is still unassigned/unverified.
- A release runbook step has accepted ownership, a mandatory execution trigger, validation and a release stop condition: it can qualify without another Issue.
- A comment says “follow-up finished” and links verified results: classify as done rather than blocking on the keyword.
- A deliberately excluded feature is mentioned in Non-goals: do not create a task unless another accepted commitment requires it.
- A migration is current AC and remains unexecuted: a newly opened follow-up does not permit successful closure.
