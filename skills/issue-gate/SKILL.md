---
name: issue-gate
description: Route an Issue or proposed change to the next needed framing, decision, or implementation-readiness check. Use when that next step is unclear; do not run every gate in sequence.
metadata:
  author: "大铭 (https://github.com/ai-daming)"
  copyright: "Copyright © 大铭"
---

# Issue Gate

Choose and execute the next necessary check. Routing does not authorize implementation, accept a design, or authorize external writes.

## Route by the unresolved question

Inspect available Issue, code, runtime evidence, accepted designs, and prior decisions first. Reuse facts already collected in this task when their source, revision, scope, and freshness still apply; investigate missing facts yourself.

| What is unresolved? | Next skill or action |
|---|---|
| Whether the problem is real, the cause is supported, or the proposed direction serves the goal | `$challenge` |
| A material trade-off owned by the user, after the framing is accepted | `$grill` |
| Whether accepted architecture covers requested coding, schema/config/migration changes, or an implementation plan | `$impl-gate` |
| Only current PR correctness | `$pr-analyze` directly; let it invoke architecture verification when needed |
| Only an Issue mutation request | `$gh-issue` directly; let it check contract impact |
| A discoverable fact | Inspect the source, then route again |

This is conditional routing, not a mandatory Challenge → Grill → Implementation Gate pipeline. Clear goals and settled decisions go directly to the needed gate. An explicit skill request still invokes that skill; a settled boundary may justify a short result without inventing objections or questions.

## Handoff and continuation

- Pass the work identity, source revisions, relevant facts, fixed decisions, accepted design, open question, and existing authorization to the selected skill. Link existing evidence rather than copying a second ledger.
- Use installed skills. If a required skill is unavailable, report the missing capability; do not fabricate a pass or ask the user for evidence you can retrieve.
- Honor the result: Challenge may require evidence, reframing, or stopping; Grill may require a user decision; Implementation Gate may require evidence, decisions, design, or acceptance.
- Once the selected check resolves its question, continue within the already authorized scope. Do not ask the user to invoke the next skill or approve routine continuation.
- A material goal change or newly introduced design still needs the appropriate user acceptance. Only `READY` permits implementation, and only when implementation authority is also present. Do not ask again for authority already granted for that exact scope.
- Do not bounce between skills on an unchanged blocker. Name the missing fact, decision, or accepted design once; investigate available evidence or wait for the required user input.

## Output

Give one short human explanation: what is being attempted, why the selected check matters, and who acts next. Add a concrete example only when needed to explain the consequence.

The selected skill's verdict and evidence are the substantive result. Do not repeat its report or print rows for every skipped skill. If a routing receipt is useful, append:

```text
Route: <selected skill/action, or none>
Reason: <material uncertainty, or existing evidence that resolves it>
Result: <selected skill's verdict, or not run>
Next: <concrete action and owner>
```

If the request ends at framing/specification, say `Ready for specification`; do not imply implementation readiness. If the implementation gate returns `READY` without execution authority, say `Ready for implementation authorization`.
