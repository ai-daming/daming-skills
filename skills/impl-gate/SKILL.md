---
name: impl-gate
description: Decide whether a software change may enter implementation by verifying an accepted architecture baseline, including both algorithms and data structures. Use before coding, or when implementation/review exposes missing ownership, lifecycle, concurrency, persistence, failure-recovery, or cross-boundary design. Do not use for general problem framing or to invent architecture during coding.
metadata:
  author: "大铭 (https://github.com/ai-daming)"
  copyright: "Copyright © 大铭"
---

# Implementation Gate

Prevent a business Issue, an acceptance checklist, or a pile of data shapes from being mistaken for an implementation-ready design.

The governing test is:

> 程序 = 算法 + 数据结构

A design is incomplete when it describes only goals and records, or only processing steps. The two sides must constrain each other: the algorithm names the state it reads and changes; each durable or shared structure names the algorithm and production consumer that use it.

This skill is a read-only readiness gate. It does not authorize coding, edit an Issue, accept an architecture on the maintainer's behalf, or replace `$challenge`, `$grill`, or architecture design.

## Inputs

Collect facts rather than asking the user to retrieve them:

- the requested implementation scope and Issue/specification;
- repository instructions, current architecture entry point, Accepted ADRs, and relevant design artifacts;
- an exact code baseline when the work is repository-bound;
- prior decisions, known constraints, affected modules and external boundaries;
- any candidate design receipt.

If these facts are unavailable, preserve the failed lookup or missing source instead of filling the gap with assumptions.

## Gate

### 1. Bind the work

Record the work identity, exact baseline, requested scope, fixed constraints, and implementation authority. Authorization to design is not authorization to implement.

### 2. Test whether existing architecture is sufficient

Trace the requested change against the accepted architecture. A named L1-L4 scheme may help, but is never required. Inspect the actual architectural impact:

- fact ownership and authority;
- state/lifecycle transitions and atomic boundaries;
- scheduling, ordering, retry, deduplication, caching, invalidation, concurrency, cancellation, restart, or recovery algorithms;
- schemas, request/response shapes, queues, events, leases, caches, files, tables, and other shared or durable structures;
- module/service/process/account/repository/worktree boundaries;
- compatibility, migration, rollback, and operational failure modes.

A large diff can remain inside an accepted design. A small change can require design when it changes one of these contracts.

### 3. Verify design completeness

When the work changes architecture, read [references/design-readiness-contract.md](references/design-readiness-contract.md) completely and audit the candidate design. Do not accept headings or field presence as proof. Follow behavior end to end and verify that every new concept has a production consumer and every critical transition has owned state and failure semantics.

Route unresolved matters precisely:

- missing repository/runtime facts → `NEEDS_EVIDENCE` and investigate;
- consequential user-owned choice → `NEEDS_DECISION` and use `$grill`;
- wrong or unsupported problem framing → `REFRAME` and use `$challenge`;
- architecture work absent or incomplete → `DESIGN_REQUIRED`;
- candidate design complete but not explicitly accepted by the maintainer → `AWAITING_ACCEPTANCE`;
- accepted design covers the exact scope and baseline → `READY`.

### 4. Issue or verify the receipt

Only `READY` may produce a `VerifiedDesignReceipt`. Use the schema and validity rules in the reference. A receipt records evidence; it does not make weak design true.

For newly introduced architecture, `READY` requires explicit maintainer acceptance of the referenced design. For work wholly inside an already Accepted baseline, record that baseline as the acceptance source.

A receipt becomes stale when the Issue identity, baseline, implementation scope, accepted design, or a material decision changes. Re-run the gate; do not edit the old receipt into apparent validity.

## Output

Lead with a human explanation, then provide the machine-like receipt. A gate code is not self-explanatory.

The human layer must answer:

1. **What is about to be built or changed?** Give enough prior context that a reader unfamiliar with the Issue can follow.
2. **Why is it ready or not ready?** Translate missing architecture into behavior: who decides order, what happens after a crash, which record is authoritative, or how conflicting writes are handled.
3. **What could go wrong if coding starts now?** Give a concrete scenario whenever the gap involves shared state, scheduling, migration, persistence, retry, concurrency, rollback, or recovery.
4. **What happens next?** Say who does the next action. If a user decision is required, end with “你现在只需要决定：…”.

Define technical terms on first use. Do not expose bare shorthand such as `L3`, `atomic boundary`, `fact owner`, `generation`, `AC4`, or a schema/table name without a short ordinary-language explanation. Exact paths, SHAs, ADRs, and type names belong in a following **Technical evidence** section.

Example for `DESIGN_REQUIRED`:

> **人话结论：现在不能开始写代码。** 我们已经知道要“减少多个工作区重复访问 GitHub”，但还没有决定谁统一排队、哪些请求可以合并、限额用完后怎么办，以及程序重启时正在排队的请求算失败还是重试。
>
> **举例：** 两个工作区同时刷新同一个 PR。如果各自维护队列，它们可能同时消耗同一账号的最后一次 API 配额；如果共用队列，又必须先定义哪个账号和哪些请求可以共享。
>
> **下一步：** 先完成并确认这套调度与重启规则，再进入实现。

After that human layer, append the exact receipt:

```text
Implementation Gate: READY | DESIGN_REQUIRED | AWAITING_ACCEPTANCE | NEEDS_EVIDENCE | NEEDS_DECISION | REFRAME
Work: <issue/task identity>
Baseline: <exact SHA or explicit non-repository baseline>
Architecture source: <accepted artifact(s), or missing>
Algorithm coverage: <complete / gaps>
Data-structure coverage: <complete / gaps>
Open material items: <none or list>
Next action: <one concrete gate>
```

For `READY`, append the receipt. For every other verdict, state the minimum missing evidence, design work, decision, or acceptance action and stop before implementation.

Before sending, apply this reader check: a technically capable reader with no repository history must understand “要做什么、缺什么、会出什么问题、下一步是什么” without decoding internal labels. If not, rewrite the human layer; do not remove the technical evidence.

## Rules

- Do not equate Issue goals, AC, tests, wire formats, class diagrams, or tables with architecture.
- Do not demand a new ADR when the accepted architecture already decides the change.
- Do not let a Coding Agent design an L2/L3 boundary incrementally while implementing it.
- Do not let a reviewer prescribe an unaccepted architecture as the only repair.
- Do not treat green CI or a successful prototype as evidence that ownership and lifecycle are designed.
- Do not validate receipts by regex or field existence alone; semantic traceability is the gate.
- Keep implementation authorization separate even after `READY`.

For calibration examples, read [references/examples.md](references/examples.md).
