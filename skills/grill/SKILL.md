---
name: grill
description: Resolve consequential user-owned trade-offs after a problem is accepted. Use when choices change scope, behavior, risk, compatibility, or rollout; do not interview the user about discoverable facts or settled decisions.
metadata:
  author: "大铭 (https://github.com/ai-daming)"
  copyright: "Copyright © 大铭"
---

# Grill

Resolve the decisions that need the user's judgment. Preserve accepted constraints and expose material assumptions without turning technical reasoning into a questionnaire.

## Establish the boundary

Identify the target, in-scope decisions, fixed constraints, deferred branches, decision authority, and what constitutes completion. Reuse an existing scope/decision record. Ask about the boundary only when competing interpretations materially change the work.

If the framing itself is unsupported, use `$challenge`. Invocation of Grill does not authorize implementation.

## Decide whether to ask

Classify each unresolved item before presenting it:

| Item | Action |
|---|---|
| Fact available from code, docs, logs, tests, or runtime | Inspect it yourself |
| Conclusion implied by accepted constraints or previous answers | Record the derivation; do not ask again |
| Technical choice delegated to the agent within the authorized scope | Decide and explain the material consequence |
| User-owned trade-off affecting scope, behavior, cost, risk, compatibility, or rollout | Ask with viable options and a recommendation |
| Only one viable path, but it needs new scope, cost, risk acceptance, or authority | Ask whether to accept that consequence, defer, or stop; do not pretend impossible options are viable |
| Complete new design awaiting acceptance | Present the complete design for acceptance; individual answers do not constitute acceptance of the assembled design |

Do not turn a recommendation into a user decision. A technically necessary mechanism may still require acceptance as part of a new architecture. Derived conclusions do not grant authority to implement it.

## Ask in dependency order

Track dependencies between material decisions. The **frontier** consists of unresolved choices whose prerequisite facts and decisions are settled. Ask only those choices, and recompute after each answer.

A single choice needs no ceremonial tree. Use an explicit tree/ledger for multiple dependent decisions, long work, or handoff. Group independent questions into a small coherent round; defer dependent questions. Investigate missing facts while progressing independent authorized work.

Each question should make the decision answerable in one reading:

- Explain what is changing and the consequence that is still undecided.
- Give viable options, observable trade-offs, and your recommendation.
- Use a concrete example or define a technical term when needed to understand the choice; do not repeat background already established in the round.
- End with exactly what the user must decide. Keep optional code symbols and evidence links separate from the business explanation.

Do not fill a fixed questionnaire or generate alternatives merely to reach an option count. If every alternative violates accepted constraints, explain the implied result instead of asking for another A/B answer.

Wait for required user-owned decisions. Record each accepted answer once, including conditions and deferred branches. Prior authority remains valid for the same scope; do not repeatedly ask to proceed between rounds that need no new decision.

## Completion and handoff

After recomputing the frontier, report only the applicable state:

- **Continue:** answerable material choices remain.
- **Investigate:** missing facts block the remaining choices; name the facts and inspect accessible sources.
- **Boundary decision:** new scope or a contradiction requires reopening a fixed choice; ask explicitly.
- **Complete:** no unresolved material choice remains inside the agreed boundary.

At completion, summarize the final decisions, material consequences, deferred work, and next action. Link the existing scope/decision record instead of duplicating it. An exhausted frontier is not completion if prerequisites are still unknown.

Continue authorized work when decisions are settled. Before implementation, `$impl-gate` must verify the completed design; a new design needs maintainer acceptance, and execution needs authority from the original request or a subsequent instruction.

## Calibration

- Accepted rule: old emergency commands must not execute after restart. If alternatives violate that rule and the agent has design authority, derive the required behavior and incorporate it into the candidate design. Do not ask the user to choose a known violation.
- New constraint: the only safe rollback requires an additional maintained binary. That introduces a cost/scope choice; ask whether to accept it or defer the change.
- Customer merge with unresolved travel-policy handling: ask whether to move the policy and how to handle conflicts. Code can reveal existing data, but cannot choose the user's business policy.
