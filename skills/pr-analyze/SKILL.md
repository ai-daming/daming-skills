---
name: pr-analyze
description: Analyze or review a GitHub pull request from a PR number, URL, or owner/repo#number. Also use when the user says review again, re-review, 重新 review, 再 review, or equivalent for the current PR. Produce an evidence-bound Chinese report covering exact base/head SHAs, prior-finding closure, invariants, CI and merge gates, code findings, scope drift, and safe next actions.
metadata:
  version: "0.14.0"
  author: "大铭 (https://github.com/ai-daming)"
  copyright: "Copyright © 大铭"
  compatibility: "Requires authenticated GitHub CLI (gh) and Git; matching local worktree preferred, isolated clone fallback."
---

# PR Analyze

Analyze the current PR facts and the exact reviewed code, then produce a structured Chinese report. Keep discovery and reporting read-only with respect to GitHub. Saving the local report and preparing isolated source are expected local side effects; GitHub review, comment, approval, or merge actions require explicit authorization.

## Inputs

Accept:

- PR number, when the repository can be resolved from the current git remote
- PR URL
- `owner/repo#number`
- a continuation such as `重新 review`, `再 review`, `review again`, or `re-review` when the current PR is unambiguous from the conversation or active task context

If repository resolution is ambiguous, ask for the repository instead of guessing.

Every review request requires a fresh current-head assessment. Refresh live PR facts and select first-review or re-review; do not carry forward the old verdict. Within the same task, reuse already read skill/reference text when the files are unchanged and that context is still available. Read new or changed references required by the current mode; reread when their content is unavailable. Reloading unchanged instructions is not review evidence.

Reuse prior reports, source inventories, and reproduction scripts as inputs to current verification. Old test results and approvals are historical, not current-head proof. Keep accepted design and user decisions separate from those expiring code-review results.

## Configuration and output

Use `config.json` adjacent to this `SKILL.md`; do not hardcode an engine-specific skills directory. It contains:

```json
{
  "report_dir": "/absolute/path/to/pr-reports"
}
```

Before analysis, validate that `report_dir` is usable. If it is absent, ask the user to choose a persistent report directory, create it only after that choice, and save the configuration beside this file.

Save reports as:

```text
{report_dir}/{owner}-{repo}/pr-{number}-{YYYYMMDD}-{HHMMSS}.md
```

## Required workflow

### 1. Resolve and freeze the review baseline

Confirm `gh` authentication and resolve `owner/repo`. Fetch live metadata including at least:

```bash
gh pr view "$PR" --repo "$OWNER_REPO" --json \
  number,url,title,body,state,isDraft,author,baseRefName,baseRefOid,\
  headRefName,headRefOid,isCrossRepository,files,additions,deletions,\
  commits,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,\
  closingIssuesReferences
```

Record `baseRefOid` and `headRefOid` as the review baseline. Names alone are not a baseline. If the PR head changes during analysis, do not mix evidence from different heads: refresh metadata, source, comments, reviews, and CI, then restart the final assessment against the new head.

Treat these gates explicitly:

- `CONFLICTING` or `DIRTY`: merge blocked
- draft: not ready for approval or merge
- `BLOCKED`, `UNSTABLE`, pending, failed, cancelled, or missing required checks: not green
- `UNKNOWN`: unresolved, not equivalent to clean

Fetch metadata, diff, and independent read-only API facts in parallel where practical, but keep failures visible with the failed action and original error.

### 2. Read requirements, existing review, and related work

Read:

- PR body, commits, and closing issues
- repository instructions such as `AGENTS.md`, `CLAUDE.md`, architecture documents, accepted ADRs, and linked requirements relevant to the change
- inline review comments
- submitted reviews
- PR conversation comments

Before treating an implementation PR as architecture-ready, inspect its accepted design baseline and any `VerifiedDesignReceipt`. When the PR creates or changes fact ownership, lifecycle, atomicity, concurrency, persistence, recovery, or a cross-module/service boundary, invoke `$impl-gate` for architecture verification. Use delta verification when prior verified design evidence is available and traceable; use full verification for uncovered boundaries or insufficient prior evidence. Both algorithms and data structures must be traced; an ADR title, receipt shape, green CI, or author claim is insufficient.

Reference the gate's result once in the review instead of copying its full report. An unchanged Accepted design does not need acceptance again merely because HEAD changed. The reviewer still independently checks whether current code implements that design.

- `READY`: record the exact architecture source, acceptance evidence, covered scope, and receipt validity at the reviewed baseline.
- `DESIGN_REQUIRED`: do not invent the missing architecture inside the review. Require a design-only maintainer confirmation round before further implementation.
- `AWAITING_ACCEPTANCE`: treat the candidate as design-complete but not yet authoritative; request maintainer design review rather than another redesign or implementation round.
- `NEEDS_EVIDENCE`, `NEEDS_DECISION`, or `REFRAME`: preserve that unresolved state and route to the named gate.

Do not demand a new design artifact merely because a PR is large. If the Accepted architecture already decides the changed behavior and boundaries, cite it and continue.

Use the GitHub APIs when available:

```bash
gh api "repos/$OWNER_REPO/pulls/$PR_NUMBER/comments" --paginate
gh api "repos/$OWNER_REPO/pulls/$PR_NUMBER/reviews" --paginate
gh api "repos/$OWNER_REPO/issues/$PR_NUMBER/comments" --paginate
```

Search for related or possibly duplicate PRs using linked-issue cross-references, explicit PR references, distinctive title/body terms, overlapping intent, and relevant open/merged PRs. Record the search inputs and call the result “possible duplicate” unless the evidence proves equivalence. On re-review, a prior related-work search may be reused only when the Issue links, PR title/body, declared scope, and relevant branch population have not changed; record that live check instead of repeating a broad search. Do not keep a “重复 PR / 关联分析” report section without either a current search or a justified current reuse check.

Summarize existing findings by reviewer. Do not clutter the report by restating them as new discoveries, but independently verify material findings and label true independent confirmation.

Determine the review mode before reading for new findings:

- `first-review`: perform the complete review against the frozen PR contract.
- `re-review`: first build a closure ledger for every prior finding (`finding`, invariant ID, contract anchor, original reproduction, claimed fix commit, current result), rerun the old reproductions, then review the delta since the last reviewed head and every invariant affected by that delta. Keep the full PR in context, but do not reset the scope as if history did not exist.

For every re-review, perform a mandatory breaker preflight before reviewing new examples:

1. Group prior findings by stable, decidable invariant rather than by round-local labels such as F2 or R7.
2. Record the invariant's fact owner, authoritative universe or justified equivalence classes, known enforcement points, and violation timeline.
3. State `NORMAL`, `DESIGN_TRIPPED`, `EVIDENCE_TRIPPED`, or prior `RELEASED` with evidence. Do not leave the breaker decision implicit.
4. Record scope-audit completeness separately as `NOT_REQUIRED`, `INCOMPLETE`, or `COMPLETE`.

When the PR or a repair changes state, lifecycle, scheduling, concurrency, caching, retry, timeout, shutdown, persistence, migration, reconciliation, or generated evidence, use the complete rules in [references/invariant-audit.md](references/invariant-audit.md) and apply the relevant audit artifact. Read them when first needed; reuse unchanged, available rules on re-review. This applies on first review as well as re-review.

On re-review, every newly introduced blocker must say whether it was introduced by the new diff or previously missed, why the prior closure ledger did not cover it, and why it must block the current PR instead of becoming a follow-up. A changed head permits fresh evidence; it does not permit moving the contract or turning a generic preference into a new gate.

During re-review, evaluate whether a repeated invariant failure or a failed closure claim has tripped a circuit breaker. When either is plausible, apply the complete rules in [references/circuit-breaker.md](references/circuit-breaker.md); read them when first needed or changed, and reuse them only while unchanged and available. Keep its two states distinct:

- `DESIGN_TRIPPED`: the same contract-anchored invariant has a second independently reachable violating enforcement point, or a repair leaves another point inside the already frozen scope unresolved.
- `EVIDENCE_TRIPPED`: a closure claim is not supported by the exact current head, the original reproduction, or the claimed collected validation.

A circuit breaker changes the required repair shape and closure evidence; it does not automatically change finding severity. Freeze the invariant, authoritative universe or equivalence classes, enforcement points, exclusions, and non-goals before prescribing a repair. Do not hardcode repository-specific registries, route names, file layouts, languages, or frameworks into the breaker analysis.

If a breaker is active and its scope audit is `INCOMPLETE`, stop completeness claims. The report may present verified partial findings, but it must not say that findings are exhaustive, that all issues are closed, or that the breaker is released. An incomplete audit forbids `APPROVE` only when the affected invariant is approval-relevant because of a blocking finding, an accepted repository gate, or an unresolved safety/correctness claim. A warning-only breaker is not silently promoted into a merge gate. `RELEASED` records closure of the breaker; it is not by itself an approval prerequisite.

`COMPLETE` is an evidence claim, not a confidence adjective. It is allowed only when the report or a saved report-adjacent artifact contains the row-level finite inventory or equivalence-class matrix, every selected row has a result at the exact head, critical interactions and exclusions are explicit, and the report links to that artifact. A summary such as “all exits checked” or a three-row category table is still `INCOMPLETE`.

### 3. Prepare exact source context

Prefer a detached worktree when a local repository already exists and its normalized remote identity matches `OWNER_REPO`. A similarly named directory or unmatched remote is not sufficient.

Use a task-specific temporary variable:

```bash
PR_ANALYZE_DIR=$(mktemp -d "/tmp/pr-analyze-${PR_NUMBER}-XXXXXXXX")
```

For a matching local repository:

```bash
git -C "$LOCAL_REPO" fetch --no-tags origin \
  "refs/heads/$BASE_REF" \
  "refs/pull/$PR_NUMBER/head"

git -C "$LOCAL_REPO" cat-file -e "${BASE_OID}^{commit}"
git -C "$LOCAL_REPO" cat-file -e "${HEAD_OID}^{commit}"
git -C "$LOCAL_REPO" worktree add --detach "$PR_ANALYZE_DIR/repo" "$HEAD_OID"
```

For no matching local repository, fall back to an isolated authenticated clone, then fetch and detach at the exact head:

```bash
gh repo clone "$OWNER_REPO" "$PR_ANALYZE_DIR/repo" -- --filter=blob:none --no-checkout
git -C "$PR_ANALYZE_DIR/repo" fetch --no-tags origin \
  "refs/heads/$BASE_REF" \
  "refs/pull/$PR_NUMBER/head"
git -C "$PR_ANALYZE_DIR/repo" checkout --detach "$HEAD_OID"
```

Verify all of the following before full-source review:

```bash
git -C "$PR_ANALYZE_DIR/repo" rev-parse HEAD
git -C "$PR_ANALYZE_DIR/repo" merge-base "$BASE_OID" "$HEAD_OID"
git -C "$PR_ANALYZE_DIR/repo" diff --check "$BASE_OID...$HEAD_OID"
```

- `HEAD` equals the recorded `headRefOid`
- both exact commits exist
- a merge base exists

If a shallow local repository lacks history, deepen incrementally and recheck. Do not silently substitute the latest base branch tip for the recorded base OID. If exact source acquisition fails, continue only in diff-only mode, include the raw failure, and lower confidence for cross-file conclusions.

Do not modify, stash, rebase, reset, or discard changes in the user's existing checkout. Do not execute code from an untrusted PR by default.

### 4. Review the code

Use the complete [references/checklist.md](references/checklist.md), reading it before first use and whenever changed or unavailable. Apply repository-specific contracts before generic preferences. On re-review, map the delta to affected checklist items and expand for shared mechanisms or changed contracts; do not recreate an unchanged checklist as new evidence.

Perform these passes:

1. Data-flow and roundtrip tracing
2. Correctness, safety, state, and concurrency invariants
3. Implementation completeness and architecture fit
4. Compatibility, migration, tests, operations, and scope drift
5. Adversarial second pass for boundary conditions and failure paths

For a stateful or evidence-sensitive change, pass 2 or pass 5 is incomplete until the selected artifacts from `invariant-audit.md` account for the affected states, transitions, producers, consumers, terminal exits, and validation oracle. Finding a few adversarial examples is not a substitute for that coverage map.

The architecture-fit pass must report the `$impl-gate` verdict when it was required, including whether the design receipt matches the Issue, baseline, scope, accepted artifact, and current material decisions. A stale or self-accepted receipt is not a pass.

By default, perform pass 5 locally and label it “本地对抗性复查”. It is not independent. Spawn an independent reviewer only when the user explicitly asks for delegation, sub-agents, or parallel review. De-duplicate its findings and label independent confirmation only when it truly came from independent context.

Every reported finding must include severity, confidence, exact path and line at the reviewed head, contract anchor, current-head evidence or reproduction, impact, minimal closure condition, and explicit non-goal. A recommendation may suggest an implementation, but unless an accepted repository design already requires it, do not turn that recommendation into the only authorized architecture. Separate:

- observed repository or GitHub fact
- inference supported by that fact
- recommendation or product judgment

### Remaining obligations and the gate they affect

During requirements and completeness review, inspect remaining work in the PR/Issue body, paginated comments, relevant accepted design, migration/runbook steps, and findings. Trace actual dependencies as well as search terms like “follow-up” or “另行执行”; a keyword is only a candidate. Reconcile completed items and exclude genuine optional ideas/non-goals with a reason. Required-source read failures are unknown, not an empty list.

For each real remaining obligation, record once whether it is done, handed over, explicitly declined by an authorized owner, or still unassigned/unverified. Handover needs a stable work/completion record, confirmed responsible person/team (or an established assignment policy), and a maintained pending-work list with a review date or actionable trigger. Existing owned release-task steps qualify; a new Issue number alone does not. Recheck receiving evidence for material changes before relying on it.

Name the affected gate and contract anchor: current implementation/merge AC cannot be discharged by another Issue; a designed, owned and enforced release prerequisite may remain open at merge while still blocking release. Do not promote every future task into a CRITICAL code finding, and do not call a later-gate dependency completed. Missing required handover is a specific process/evidence blocker for the gate it governs. A risk waiver cannot silently rewrite AC or authorize a new design.

If a proposed merge would auto-close linked Issues, verify their current closing AC and handover dispositions before recommending or executing that merge. If auto-closure would falsely mark unfinished work complete, stop that merge; propose an explicitly authorized correction to the closing relationship/contract instead. Do not treat this check as permission to edit Issues, create tasks, or assign others.

### Human-readable review contract

Lead with the observable problem, then the evidence and observable closure condition. Explain a necessary term on first use and give a concrete timeline for an indirect, concurrent, or recovery failure. Do not repeat background already explained in the report. Preserve severity, confidence, contract anchor, exact location, current evidence, impact, minimal closure, and non-goals for each finding; the format can be a paragraph or a table when that is enough.

Use [references/report-template.md](references/report-template.md) for presentation. Each fact and ledger has one full location; summaries and gate handoffs reference it. A reader should understand what fails, who is affected, why it blocks (if it does), and what behavior closes it without decoding private shorthand.

Do not infer severity merely from the checklist section containing an item. A performance issue such as N+1 is CRITICAL only when demonstrated impact satisfies the CRITICAL definition.

Apply an Occam gate to every requested new concept (type, protocol field, table, generator, canary, primitive, or layer). Before requiring it, name the acceptance criterion it closes, the production consumer that reads its value, the final-behavior difference if it is removed, and why an existing mechanism cannot express the invariant. If any answer is missing, prefer reuse or deletion. Occam is a tie-breaker between sufficient fixes, not an independent blocker and not a line-count contest.

The visible review identity is always `**身份：Review Agent**`. Use `LGTM` only when the exact current head qualifies for APPROVE: no blocking finding, non-draft, green required gates, stable baseline, and completed required verification. Never use `LGTM` for COMMENT, REQUEST CHANGES, WAIT, stale heads, or incomplete gates.

### 5. Validate proportionally and safely

Use current GitHub CI as live evidence. Distinguish passing, failing, pending, skipped, cancelled, absent, and stale checks.

For a trusted repository, run repository-defined read-only validation when the user requests it or when it is clearly part of the requested review scope. Read project instructions first, record exact commands and results, and distinguish PR regressions from failures already present at the base baseline.

On re-review, rerun prior reproductions at the exact current HEAD, verify the repair delta and affected invariants, and complete repository-required checks. Reuse current-head CI where it supplies the required evidence. Broaden local tests when changed shared mechanisms, new failures, or unresolved risks justify it; do not repeat an unchanged successful run merely to add another receipt. Required real-storage, concurrency, coverage, and independent-review gates remain in force.

Never execute arbitrary build, test, install, or hook code from an untrusted PR without explicit authorization. Absence of local execution must be stated; it is not evidence that tests pass.

When the review creates a reproduction script, fixture, query, or non-trivial command sequence that may be needed in the next re-review, do not leave the only copy under `/tmp`. Save a report-adjacent reproduction package under:

```text
{report_dir}/{owner}-{repo}/artifacts/pr-{number}-{YYYYMMDD}-{HHMMSS}/
```

Record the exact head, command, script or request body, SHA-256, exit code, relevant output, and any environment/dirty caveat. The next review still reruns it at the new exact head; the package is durable history, not current evidence. A simple standard repository command needs only a command/result row, not a copied wrapper script.

### 6. Re-read live facts before the verdict

Immediately before the final verdict, re-fetch:

- current `headRefOid` and `baseRefOid`
- merge state and draft state
- CI checks
- reviews and material comments added during analysis

If the head changed, the previous code review is stale. Restart or clearly stop without issuing an approval verdict. Bind the report to the exact final reviewed SHA.

### 7. Generate the report

Read [references/report-template.md](references/report-template.md) and use it as the report contract. Write two layers: a short decision brief that a maintainer can understand in one pass, followed by a technical evidence appendix. State each fact once and reference it later; do not repeat the same finding in TL;DR, breaker tables, scope tables, validation, and final conclusion.

Use the template's applicable sections, not an obligatory empty form. Always retain the exact base/head, final live readback, source/evidence boundaries, current findings, validation and next action. On re-review retain the previous HEAD, reviewed delta, closure ledger, invariant/breaker preflight and scope-audit result. Include architecture verification, detailed row-level audits, active/released breaker evidence, reproduction packages and mutation previews when their triggers apply.

A section omitted as irrelevant must not hide an unperformed required check. Distinguish `not applicable` from `not verified`. Keep the human-readable layer in any GitHub body, along with each finding's severity, exact evidence, impact, closure condition and non-goal. Do not turn the decision brief into a second technical appendix.

Reserve words such as “全部关闭”, “一次收齐”, “完整覆盖”, `exhaustive`, and equivalent completeness claims for a `COMPLETE` frozen audit with recorded exclusions and evidence. Otherwise say “在当前已验证范围内” and list the unverified boundary.

Save the full report. In chat, return the substantive decision brief plus the report path; do not paste the technical appendix again unless the user asks. State the completed gate precisely: analysis, code review, local validation, GitHub review submission, approval, and merge are separate outcomes.

### 8. GitHub mutation protocol

Analysis does not authorize a GitHub mutation. If the user asks to comment, approve, request changes, or merge:

1. Refresh the target PR and exact head.
2. Prepare the exact action and complete review/comment body. Reuse an already presented identical body; do not render a second full copy solely for ceremony.
3. Check existing explicit authorization for that target, reviewed HEAD, action, and body. If it covers this exact plan, proceed without asking again; otherwise show the concrete plan and obtain authorization. A material change needs renewed authorization. A review request alone is not permission to publish or merge. Before writing, recheck that the HEAD and material review/CI facts still support the plan; if not, reassess before proceeding.
4. Write the body to a local file and use `--body-file`; never interpolate untrusted or generated review text inside a shell-quoted `--body` argument.
5. Execute only the authorized action.
6. Read the resulting GitHub review/comment or merge state back and report its URL, author, state, and head SHA.

Authorization must still be in force, not revoked or narrowed. It covers the intended write once, not repeated publication. Before retrying an uncertain mutation, read back whether it already took effect; do not blindly replay it or interpret a failed lookup as absence. If the outcome remains unknown, report it and stop the retry.

Every review/comment body starts with `**身份：Review Agent**`. An authorized APPROVE body includes `LGTM`; other actions must not include it.

Approval never implies merge authorization. Merge must be explicitly included in the preview and authorization.

### 9. Temporary source lifecycle

Do not automatically delete retained source at the end of analysis. Report the exact directory and whether it is a worktree or clone. When cleanup is authorized:

- remove a worktree with `git worktree remove` from its owning repository, then verify `git worktree list`
- remove a clone only after resolving and validating the exact temporary path; prefer a recoverable trash operation

Never use a broad or unresolved recursive deletion target.

## Severity calibration

- `CRITICAL`: a demonstrated runtime bug, security vulnerability, data loss/corruption path, or correctness failure reachable in a normal scenario without an effective safety net; blocks approval
- `WARNING`: meaningful abnormal behavior or operational risk with limited impact or an effective safety net; normally should be fixed, but does not automatically block
- `INFORMATIONAL`: maintainability, clarity, or design improvement; non-blocking

Confidence:

- `9-10`: verified through exact code path, reproduction, or authoritative evidence
- `7-8`: strong code-path evidence with a small unverified assumption
- `5-6`: plausible concern requiring verification; label it clearly
- below `5`: normally omit from main findings unless the potential impact is exceptional

## Failure handling

Do not bury errors. For every skipped or degraded step, preserve the failed action, original error text, impact on confidence, and fallback used. “Unavailable” is a result category, not a substitute for evidence.
