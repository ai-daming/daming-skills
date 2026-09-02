# Re-review Circuit Breaker

Use this protocol only during re-review when a contract-anchored invariant appears to have failed repeatedly or a prior closure claim lacks exact-head evidence. It is repository-, language-, framework-, and architecture-neutral.

## Purpose

The circuit breaker stops example-by-example patching and unsupported closure claims without giving the reviewer permission to invent new requirements or expand scope indefinitely.

It changes the required repair shape and closure evidence. It does not replace ordinary severity calibration, and it is not an independent merge gate.

## Definitions

### Invariant

An invariant is a decidable correctness proposition anchored to an accepted source such as an issue acceptance criterion, architecture decision, repository rule, protocol contract, schema constraint, or established safety property.

Use the proposition—not a filename, function, test case, or reviewer wording—as the identity of the invariant. Two observations belong to the same invariant only when they depend on the same required outcome and compatible fact ownership or enforcement authority.

### Enforcement point

An enforcement point is an independently reachable place where the invariant must be preserved or decided. Multiple inputs that reach the same defective decision or mutation point count as one violation point. Different files, functions, or entry names do not by themselves prove independent roots.

Two points may count separately when each can violate the invariant without traversing the other and each requires its own enforcement or delegation to a shared authority.

### Authoritative universe

The authoritative universe is the source that defines the relevant population of enforcement points or consumers. Depending on the repository, it may be a registry, router, command table, schema, interface implementation set, dependency graph, event catalog, generated manifest, or another accepted source of truth.

Do not begin from only the files changed in the latest diff when the invariant applies to a broader authoritative universe.

For finite enumerable universes, inspect every member. For open or combinatorial spaces, declare justified equivalence classes, boundary cases, critical interactions, and impossible or excluded combinations. “Complete” means complete against this frozen model, not an unbounded Cartesian product.

## States

### `NORMAL`

No circuit breaker is active. A first observed violation is handled through the normal finding and repair process.

### `DESIGN_TRIPPED`

Use this state when either condition holds:

1. The same anchored invariant has a second independently reachable violating enforcement point, whether found on the same head or a later head.
2. After a repair, another enforcement point already inside the previously declared scope still violates the invariant.

This state means local example patches are no longer sufficient evidence of closure. It does not prescribe a particular architecture; a shared enforcement mechanism, exhaustive local corrections, deletion, or another minimal sufficient design may all be valid if they cover the frozen universe.

### `EVIDENCE_TRIPPED`

Use this state when a closure claim fails verification, including when:

- the exact reviewed head does not contain the claimed production change;
- the original reproduction still fails;
- the claimed test is not collected, not run, stale, or does not exercise the stated boundary;
- the disposition describes a different diff, head, environment, or outcome from the one reviewed.

Evidence failure does not by itself prove that the design must be redone. First rebuild exact-head evidence. Upgrade to `DESIGN_TRIPPED` only if that verification shows that the implementation or declared scope is incomplete.

### `RELEASED`

The breaker was active and all applicable release conditions below are satisfied at the exact current head. Record the prior state and release evidence in the closure ledger; do not erase the history.

## Classification axes

Do not force a mutually exclusive single cause. Record both axes when useful:

1. **Code origin**: `pre-existing`, `new-diff`, or `persisted-after-repair`.
2. **Closure failure**: `missed`, `incomplete-design`, `not-landed`, `regression`, or `evidence-mismatch`.

More than one label may apply. Labels explain the timeline; the breaker state determines the required next evidence.

## Breaker decision frame

When a breaker is triggered or seriously considered, the review must state:

1. **Invariant and anchor**: the decidable proposition and exact accepted contract location.
2. **Violation timeline**: reviewed SHA, entry or enforcement point, reproduction, and classification axes for each occurrence.
3. **Breaker state**: `DESIGN_TRIPPED` or `EVIDENCE_TRIPPED`, with the specific trigger condition.
4. **Frozen scope**:
   - authoritative universe or equivalence-class model;
   - known enforcement points and consumers;
   - exclusions and why they are outside the invariant;
   - explicit non-goals.
5. **Required closure package**: only the artifacts and observable behavior needed to release this breaker.
6. **Scope-audit completeness**: `INCOMPLETE` until the required inventory or equivalence-class matrix is actually accounted for; `COMPLETE` only with inspectable coverage and exclusions.

If the reviewer cannot anchor the invariant or freeze a bounded scope, do not trip the breaker. Report the uncertainty or ordinary finding instead.

## Required actions

### For `DESIGN_TRIPPED`

Stop accepting a patch justified only by the latest counterexample. Require a closure package appropriate to the invariant:

- a complete form of the invariant over the frozen universe;
- an inventory, call/data-flow graph, state-transition map, consumer map, or equivalent artifact derived from the authoritative source;
- a test matrix covering every finite member, or justified equivalence classes, boundaries, and critical interactions for open spaces;
- implementation evidence mapping every in-scope enforcement point to its mechanism and validation;
- explicit exclusions and non-goals.

The reviewer may require the evidence shape, but must not mandate a new abstraction or unique architecture when an existing mechanism can express the invariant. Apply the Occam gate.

Read and apply [invariant-audit.md](invariant-audit.md). Select the artifacts required by the invariant: a state-transition and terminal-exit matrix, producer-consumer and reconciliation matrix, change-impact frontier, evidence/oracle audit, or a justified subset. Finding additional examples while this audit remains `INCOMPLETE` does not constitute another completed re-review.

### For `EVIDENCE_TRIPPED`

Suspend the closure claim and rebuild evidence before requesting redesign:

- freeze and reread the exact head;
- show the claimed diff at that head;
- rerun the original reproduction;
- confirm test discovery/collection and the exercised production boundary;
- read back generated, committed, CI, or GitHub state relevant to the claim.

If these checks prove the intended implementation is absent, land and verify it. If they reveal additional in-scope enforcement gaps, upgrade to `DESIGN_TRIPPED`.

Evidence used to close the breaker is itself in scope for review. A test, harness, generated report, or metric must have a real oracle, an applicable negative control, exact-head provenance, and a measurement window that covers the claimed behavior. An unconditional pass or stale artifact keeps the breaker at `EVIDENCE_TRIPPED`.

## Hard stop while audit is incomplete

Breaker state and scope-audit completeness are separate axes:

```text
breaker: NORMAL | DESIGN_TRIPPED | EVIDENCE_TRIPPED | RELEASED
scope audit: NOT_REQUIRED | INCOMPLETE | COMPLETE
```

When `DESIGN_TRIPPED` or `EVIDENCE_TRIPPED` is active and the applicable audit is `INCOMPLETE`:

- verified examples may be reported as partial evidence;
- the report must list the unverified authoritative members, classes, transitions, consumers, or oracle properties;
- the reviewer must recommend `WAIT` or a non-approval action when the invariant is approval-relevant because of a blocking finding, accepted gate, or unresolved safety/correctness claim;
- the reviewer must not say “全部关闭”, “一次收齐”, “完整覆盖”, `exhaustive`, or an equivalent;
- the reviewer must not issue `APPROVE` or `LGTM` while an approval-relevant audit is incomplete.

This stop prevents serial counterexample review. It does not turn a warning-only breaker into an independent merge gate, and it does not prevent an explicitly authorized comment that clearly says the audit is incomplete.

## Scope freeze and anti-goalpost rule

Once a breaker decision is issued, freeze its invariant, universe or equivalence classes, enforcement points, exclusions, and non-goals before the repair begins.

On the next review, do not silently enlarge that frozen scope. A newly observed point outside it must be classified as one of:

- evidence that the original authoritative universe was incorrectly derived, with an explicit amendment and explanation;
- a new invariant and first finding;
- a separate root that belongs in follow-up work.

Any amendment must explain why the prior review missed it and why it must affect the current PR. A changed head allows new evidence, not moving acceptance criteria.

## Severity and decision boundary

Breaker state and finding severity are independent:

- severity follows demonstrated reachability, impact, and safety nets;
- the breaker controls what counts as sufficient repair and closure evidence;
- a breaker does not automatically turn a warning into a blocker;
- breaker release is not an independent approval prerequisite when every remaining finding is legitimately non-blocking and no repository gate requires closure;
- an unresolved blocking finding remains blocking for its ordinary reason, not merely because the breaker is active.

Do not use a breaker to prevent a legitimate follow-up when the observed problem is outside the frozen invariant or has an effective safety net consistent with repository policy.

## Release conditions

Release the applicable breaker only when all required conditions hold at the exact current head:

1. All original reproductions for the invariant pass.
2. The frozen finite universe is fully accounted for, or the declared equivalence classes, boundaries, and critical interactions are covered.
3. No in-scope enforcement point remains unresolved or silently excluded.
4. The repair author has added at least two adjacent cases not supplied by the reviewer, unless a stricter repository rule applies.
5. Production diff, collected tests, executed validation, and disposition claims agree.
6. Exclusions and non-goals remain explicit.
7. Re-review records the prior state, exact release SHA, evidence, and result as `RELEASED`.

Passing a matrix is not sufficient if it replaces the production decision, persistence, transaction, concurrency, or protocol boundary with a mock contrary to repository policy.

## Independent-root exception

Do not trip a shared design breaker merely because two findings use similar words. Treat them as independent only when evidence shows materially different contract anchors or fact owners/enforcement authorities and different closure mechanisms. Different files, endpoints, or counterexample strings are not enough.

Record the exception and its evidence in the closure ledger so a later review can challenge it. If the supposed independent roots converge on the same authority boundary, treat them as the same invariant and apply the breaker.

## Reporting

Reports should show `NORMAL`, `DESIGN_TRIPPED`, `EVIDENCE_TRIPPED`, or `RELEASED` and include the decision frame whenever the state is not `NORMAL`.

Every re-review report also shows scope-audit completeness. A contextual request such as “重新 review” starts a fresh skill invocation and breaker preflight against the live head; it never inherits a prior `RELEASED`, `COMPLETE`, or green-CI claim without revalidation.

Do not claim that the breaker would have saved a specific number of review rounds unless a controlled comparison exists. Project-specific retrospectives may discuss counterfactual estimates, but they are examples, not universal rules.
