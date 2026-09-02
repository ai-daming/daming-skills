# Invariant Audit

Use this reference when a PR changes state, lifecycle, scheduling, concurrency, caching, retry, timeout, shutdown, persistence, migration, reconciliation, or generated evidence. It turns “look for more edge cases” into a bounded coverage argument.

## Purpose

A reviewer cannot prove that arbitrary software has no bugs. The reviewer can prove what was inspected against a frozen model and must not call a few examples exhaustive.

The audit answers:

1. What observable proposition must always hold?
2. Who owns the facts used to decide it?
3. Which finite members or justified equivalence classes are in scope?
4. Which transitions, producers, consumers, terminal exits, and critical interactions were checked?
5. What remains unverified?

Use plain language before internal names. For example:

> 人话：一个请求无论成功、失败、超时还是关闭，都必须从“正在处理”中消失一次，而且调用方只能收到一个最终结果。

Then record the technical invariant:

```text
INV-1: every admitted request reaches exactly one terminal outcome and no terminal request remains in an active-state collection.
```

## 1. Stable invariant ledger

Track invariants across review rounds. Finding labels are local references, not invariant identity.

| Invariant ID | Plain proposition | Contract anchor | Fact owner | Authoritative universe / classes | Violations | Breaker state | Audit completeness |
|---|---|---|---|---|---|---|---|
| INV-1 | ... | ... | ... | ... | SHA + enforcement point | NORMAL / DESIGN_TRIPPED / EVIDENCE_TRIPPED / RELEASED | NOT_REQUIRED / INCOMPLETE / COMPLETE |

Rules:

- Reuse the invariant ID when a later finding has the same required outcome and authority boundary, even when its file, endpoint, test, or round label changed.
- Create a new invariant only when the contract anchor or decision authority is materially different.
- Record both newly introduced violations and violations that were previously missed.
- A changed finding title never resets the violation history.

## 2. Derive the authoritative scope

Do not start from only the changed lines. Choose the smallest source that actually defines the population:

- interface implementations or callers;
- route, command, event, operation, or schema registries;
- readers and writers of the owned state;
- state collections and transition functions;
- producers and production consumers of a field or event;
- generated manifests or static access gates;
- justified equivalence classes when the input space is open.

Record exclusions and why they cannot violate this invariant. “Not changed in this diff” is not a sufficient exclusion when it reads or writes the affected fact.

For a finite universe, account for every member. For an open space, cover boundaries and critical interactions without inventing an infinite Cartesian product.

## 3. Select the required audit artifacts

Use only the artifacts relevant to the invariant, but complete each selected artifact before claiming closure.

### A. State-transition and terminal-exit matrix

Required when a value moves through states, queues, leases, tasks, transactions, retries, or shutdown.

| Current state | Event / decision | Next state | State removed or released | Caller-visible result | Evidence emitted | Enforcement point | Verified |
|---|---|---|---|---|---|---|---|
| queued | deadline expires | terminal | queue membership | timeout once | terminal event once | ... | yes/no |

Enumerate every independently reachable exit, including:

- success and ordinary failure;
- rejection before work starts;
- timeout before admission, during waiting, during execution, and after an uncertain result where reachable;
- cancellation and shutdown;
- retry, duplicate delivery, and late completion;
- partial success and cleanup failure.

Check the conservation rule when applicable:

```text
each live item belongs to exactly one active state;
each terminal transition removes it from all active states exactly once;
each caller observes at most one terminal result.
```

### B. Producer-consumer and reconciliation matrix

Required when a fact, classification, identity, version, quota, status, or evidence value is produced in one place and consumed elsewhere.

| Fact / semantic identity | Producer | Value before external result | Value after authoritative result | Production consumers | Reconciliation rule | Missing/unknown rule | Verified |
|---|---|---|---|---|---|---|---|
| resource identity | request classifier / response | predicted or unknown | authoritative value | admission, reservation, settlement | ... | ... | yes/no |

Check both directions:

1. Every produced value has a real production consumer.
2. Every consumer reads from the authoritative producer or an explicit reconciliation rule.
3. A provisional value cannot silently survive after contradictory authoritative evidence.
4. Missing evidence remains unknown unless an accepted fail-closed rule says otherwise.
5. Settlement releases or charges the same semantic identity that admission reserved, or an explicit transfer reconciles them.

### C. Change-impact frontier

Required for a repair that changes shared state or a common decision mechanism.

Inventory:

- state fields and collections added, removed, or reinterpreted;
- all readers, writers, deleters, expiry paths, and serializers;
- all decisions whose result depends on them;
- all terminal exits and cleanup paths affected by the change;
- tests and operational evidence that observe the production boundary.

The review delta is the starting point. The impact frontier is the complete set of consumers and transitions reached from that delta.

### D. Evidence and oracle integrity audit

Required when tests, measurement scripts, generated reports, counters, lifecycle events, coverage artifacts, migration previews, or other evidence are used to close a finding or acceptance criterion.

| Claim | Measured boundary | Input window | Oracle / formula | Negative control | Exact-head provenance | Dirty/tool identity | Result |
|---|---|---|---|---|---|---|---|
| threshold holds | production adapter | event A → event B | actual comparison | threshold+1 fails | SHA | clean + tool hash | valid/invalid |

Verify:

- the oracle contains a real comparison; unconditional success is invalid;
- a negative control demonstrates that the oracle fails when the requirement is violated;
- formulas include every applicable success and non-success terminal class;
- the measurement window includes all events claimed and excludes unrelated contamination explicitly;
- generated evidence records the exact head, dirty state, environment, and tool identity when these affect reproducibility;
- the recorded tool and source match the exact current head;
- the test or harness crosses the production decision boundary instead of replacing it;
- CI collection and execution agree with the claimed local evidence.

An invalid oracle triggers `EVIDENCE_TRIPPED`; it cannot release a design breaker even when the implementation may be correct.

## 4. Critical interactions

After completing each individual row, test interactions that can change ownership or ordering. Choose those supported by the architecture, such as:

- admission followed by authoritative reclassification;
- timeout concurrent with dispatch;
- cancellation concurrent with settlement;
- shutdown while an item is between two named states;
- retry after success with response loss;
- cache invalidation concurrent with a reader;
- old-version producer with new-version consumer;
- evidence flush split across an unfinished operation.

Do not test every pair mechanically. Explain why the selected interactions cross distinct authority, atomicity, ordering, or lifecycle boundaries.

## 5. Completeness decision

Record one value per invariant:

- `NOT_REQUIRED`: the invariant does not need a scope audit; explain why.
- `INCOMPLETE`: the authoritative scope or a required artifact still has unverified rows.
- `COMPLETE`: every finite member or justified class, required boundary, selected critical interaction, exclusion, and evidence oracle is accounted for at the exact head.

`COMPLETE` is bounded by the frozen model. It is not a claim that arbitrary software has no undiscovered bugs.

When `INCOMPLETE`:

- report verified findings as partial;
- list the unverified boundary;
- do not say “全部关闭”, “一次收齐”, “完整覆盖”, or equivalent;
- do not release an active breaker;
- do not approve.

### `COMPLETE` eligibility

`COMPLETE` requires inspectable row-level proof, not the reviewer's memory or a category summary. All of the following must hold:

1. The authoritative finite members or justified equivalence classes are written down.
2. Every selected matrix row records the exact enforcement point or boundary, exact-head result, and verification method.
3. Critical interactions, exclusions, and non-goals are explicit.
4. The full matrix appears in the report or in a durable report-adjacent artifact linked from it.
5. The artifact can be reread without access to transient chat reasoning or a deleted `/tmp` file.

A statement such as “all exits were inspected,” a count without the member list, or a three-row summary of broad categories is `INCOMPLETE`. If the full matrix would make the decision brief unreadable, place it in the technical appendix or an artifact; do not weaken the proof.

A green test suite alone is not a completeness argument.

### Durable reproduction index

When a reproduction materially supports a finding or breaker decision, record:

| Repro ID | Invariant | Exact head | Durable script/request | SHA-256 | Command | Exit/result | Environment caveat |
|---|---|---|---|---|---|---|---|
| REPRO-1 | INV-1 | ... | report-adjacent path | ... | ... | ... | ... |

The saved reproduction is historical evidence. Re-review must rerun it against the new exact head and record the new result rather than inheriting the old result.

## 6. Human-readable handoff

For each invariant, explain:

1. **人话结论**: what real situation can fail.
2. **举例**: one concrete sequence a reader can picture.
3. **审查范围**: what states, producers, consumers, or classes were checked.
4. **还没验证什么**: explicit residual boundary.
5. **怎么才算修好**: observable closure behavior.

Keep tables as technical evidence after the explanation; do not make the reader decode the table to learn the problem.

---

Copyright © 大铭 · [github.com/ai-daming](https://github.com/ai-daming)
