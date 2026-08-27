---
name: grill
description: Resolve material decision ambiguity in a coding plan, design, or specification using a dependency-aware decision tree and frontier. Use after the problem framing is accepted and user-owned choices must be settled before execution.
---

# Grill

Turn an accepted problem into shared, explicit decisions before implementation. Model dependencies between decisions, ask only what can be decided now, and end with no silent in-scope assumptions.

## Invocation

Invoke with `$grill` when a plan, design, migration, API, schema, workflow, or rollout contains consequential unresolved choices. Use it after framing is accepted; if the problem itself may be wrong, pause and recommend `$challenge`.

Do not use it for facts the agent can inspect, trivial preferences with no downstream effect, or work whose material decisions are already fixed. Invocation does not authorize implementation.

## Establish the Decision Boundary

Before questioning, state a compact scope contract:

- **Target:** the artifact, behavior, or outcome being decided
- **In scope:** categories of decisions this session must settle
- **Fixed:** confirmed constraints and prior decisions that will not be reopened
- **Out of scope:** adjacent branches intentionally excluded
- **Authority:** which choices require the user and which are delegated to the agent
- **Done:** the evidence that all material in-scope decisions are resolved

Ask the user to resolve the boundary only when competing interpretations would materially change the tree. Otherwise state a reasonable boundary and let the user correct it.

## Decision Tree and Frontier

Represent each material choice as a decision node. Add an edge when one decision cannot be answered responsibly until another decision or fact is settled.

The **frontier** is the set of unresolved in-scope decision nodes whose prerequisites are resolved. Ask only frontier questions. A node that depends on another open node belongs in a later round.

Recompute the tree and frontier after every answer: decisions may add, remove, or reshape downstream branches. Do not preserve questions that are no longer relevant.

## Facts vs. Decisions

- **Facts are the agent's work.** Inspect the repository, documentation, logs, tests, runtime, or other authorized sources. Do not ask the user to perform lookups available to the agent.
- **Decisions belong to the stated authority.** Ask the user for user-owned trade-offs; make delegated choices directly and record them.
- If a required fact is unknown, mark it as an unresolved prerequisite and investigate it. Continue with independent frontier nodes when possible.
- Label uncertainty honestly. Do not convert an inference into a fact merely to unlock the tree.

## Run a Round

Ask the currently answerable material decisions in a numbered round. Keep independent questions together; split an unusually large frontier into coherent batches without asking downstream questions early.

Every question must include:

1. the decision and why it matters;
2. viable options and meaningful trade-offs;
3. the agent's recommended answer and rationale;
4. any consequence that the recommendation unlocks or rules out.

Use this compact form:

```markdown
### Q1 — <decision>
<context and options>

**Recommendation:** <answer and reason>
```

Wait for user-owned decisions before treating them as settled. Record accepted answers in a decision ledger, including any condition or deferred branch.

## Completion and Handoff

After each round, classify the state:

- **Continue:** the frontier contains unresolved decisions.
- **Investigate:** no decision is currently answerable because unresolved facts block remaining nodes. Report the facts being checked; this is not completion.
- **Boundary decision:** progress requires expanding scope or reopening a fixed decision. Ask explicitly; do not expand silently.
- **Complete:** after recomputation, no unresolved material decision remains inside the agreed boundary. The in-scope tree is exhausted, not merely blocked.

At completion, provide:

- the final scope boundary;
- the decision ledger;
- material consequences and risks;
- out-of-scope or deliberately deferred items;
- the recommended next action.

Do not implement until the user separately authorizes execution or the original request already granted that authority.

## Rules

- Ask decisions, not vague requests for “thoughts.”
- Recommend an answer to every question; do not outsource all judgment to the user.
- Do not ask dependent questions in the same round as their unresolved prerequisites.
- Do not reopen settled decisions without new evidence, a contradiction, or explicit user direction.
- Do not force cosmetic or low-impact preferences into the tree.
- Surface contradictions between answers immediately.
- Preserve raw facts, agent inferences, recommendations, and user decisions as distinct records.
- Respect the agreed boundary even when interesting adjacent questions appear.

## Anti-patterns

- A flat checklist that ignores dependencies
- Asking every conceivable question at once
- Asking the user to inspect code or retrieve facts the agent can access
- Questions without a recommendation
- Treating the recommendation as the user's decision
- Expanding scope whenever a new branch appears
- Declaring success because the frontier is temporarily blocked
- Endless interviewing after all material in-scope decisions are settled
- Quietly beginning implementation at the end of the session
