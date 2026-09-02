---
name: grill
description: Resolve material decision ambiguity in a coding plan, design, or specification using a dependency-aware decision tree and frontier. Use after the problem framing is accepted and user-owned choices must be settled before execution.
metadata:
  author: "大铭 (https://github.com/ai-daming)"
  copyright: "Copyright © 大铭"
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

1. the background: what is being changed and what is currently undefined;
2. a plain-language definition of every necessary project or technical term;
3. one concrete example whenever the choice affects stored data, migration, concurrency, rollback, evidence, compatibility, or user-visible behavior;
4. viable options and their observable consequences;
5. the agent's recommended answer and rationale;
6. one final sentence saying exactly what the user needs to decide.

Do not begin with compressed codes such as `D1`, `AC4`, `source/target`, `preview hash`, or a table name. A label may be retained for the ledger only after a descriptive title. Put code symbols, table names, field names, and contract references in a final **Technical mapping** line; they support the explanation but do not replace it.

If a smart engineer unfamiliar with the repository could not answer the question without asking “这些词是什么意思、前因后果是什么,” the question is not ready to ask. Rewrite it first. When several questions introduce different unfamiliar concepts, prefer one or a small coherent batch rather than a dense four-item dump.

Use this compact form:

```markdown
### Q1 — <plain-language decision>

**背景：** <what is happening now and why this decision appears>

**举例：** <a concrete before/after scenario; omit only when the consequence is already self-evident>

**选项：**

- A: <observable consequence>
- B: <observable consequence>

**Recommendation:** <answer and reason>

**你现在只需要决定：** <one direct question>

**Technical mapping:** <optional symbols, tables, fields, issue/AC references>
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
- Asking with unexplained internal shorthand and expecting the user to reconstruct repository context
- Listing table/field names as if they explain the business consequence

## Calibration example

Bad:

> D4: `business_profiles` 是否迁移？不迁则 #62 scan 残留。

Good:

> ### Q4 — 合并客户时，差旅配置要不要一起搬过去？
>
> **背景：** 系统准备把客户 B 合并到客户 A。客户 B 还有一份独立的差旅配置；当前设计只说了联系人等四类资料怎么迁移，没有说这份配置怎么办。
>
> **举例：** 如果不搬，合并后差旅配置仍指向已经被合并掉的客户 B。后续清理程序会认为“还有资料没迁完”，也可能让客户 A 看不到原来的差旅规则。
>
> **选项：** A. 一起迁移，并规定 A/B 都有配置时保留哪份；B. 明确不迁移，并让残留检查排除它。
>
> **Recommendation:** 选择 A，因为它符合“客户合并后资料仍可用”的直觉；同时需要定义冲突规则。
>
> **你现在只需要决定：** 差旅配置是否随客户一起迁移？如果两边都有配置，保留 A、保留 B，还是阻止合并？
>
> **Technical mapping:** `business_profiles`；source = 被合并的客户 B，target = 保留的客户 A。
