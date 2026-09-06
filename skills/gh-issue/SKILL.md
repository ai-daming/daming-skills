---
name: gh-issue
description: Safely create, update, comment on, classify, relate, and close GitHub Issues while preserving the target repository's Issue evidence contract. Use for any GitHub Issue mutation. Refresh authoritative facts, distinguish framing, delivery-contract, design, acceptance, history, and metadata changes, preview their downstream invalidation, require exact authorization, execute only the authorized writes, and read GitHub back to verify the result.
---

# GitHub Issue Operator

Operate GitHub Issues through one governed mutation workflow. GitHub is the authority for Issue content, classification, relationships, Milestone membership, comments, and state. Local tools may normalize these facts but must not redefine them.

## Select the mutation path

Resolve the exact action and target first. Issue mutations use this skill; PR review/comment/approval/merge uses `$pr-analyze` directly, without running both mutation protocols for the same write.

| Mutation | Required depth |
|---|---|
| Append history-only COMMENT | Check target identity, relevant current context, exact body, authorization, and readback. Do not migrate the Issue format or audit unrelated design/AC/dependency fields. If the text changes the contract or claims acceptance/completion, use the corresponding deeper path. |
| Metadata-only change | Check repository semantics for the changed field, its current value, relevant relationships, and downstream impact. A contract-bearing label or Milestone is not automatically metadata-only. |
| CREATE, contract/framing/design or relationship change | Apply the full contract and impact workflow below. |
| Acceptance evidence, CLOSE, or REOPEN | Check the affected criteria, lifecycle rules, and evidence; CLOSE requires the completion checks below. Do not infer delivery from a design PR or an agent statement. |

For a simple path, use a compact target/action/body-or-diff/impact/authority record. Keep the same safeguards, but omit inapplicable tables. Reuse repository policy already read when its revision and applicability remain current.

## Load the Issue contract

Before planning CREATE or UPDATE:

1. Read the target repository's instructions, Issue templates, supported labels or native types, and declared Issue contract.
2. Treat that repository-owned contract as authoritative. Do not copy another repository's headings, classifications, labels, or lifecycle concepts into it.
3. If no repository contract exists, require the minimal semantic content: problem and evidence status, goal, checkable Acceptance Criteria, and direct dependencies.
4. Distinguish confirmed contract, unresolved decisions, Agent recommendations, historical evidence, and inferred intent. Missing required meaning must be reported, not invented.
5. A missing optional boundary is not automatically an explicit empty value. Preserve `unknown` when repository policy distinguishes unknown from none.

For ClickVibe, read `docs/issue-contract.md`. Do not hardcode its canonical fingerprint fields or algorithm in this Skill.

## Existing Issue compatibility

For mutations that require contract classification under the selected path, classify the Issue contract status:

```text
current | legacy-compatible | unknown | conflicting
```

- CREATE must satisfy the repository's current minimum contract.
- An existing ClickVibe Issue that still has the former minimum semantics—goal, checkable Acceptance Criteria, and direct dependencies—may be `legacy-compatible`; do not invalidate it merely because newer headings are absent.
- Missing newer semantics remain `unknown`, not an empty list or implicit permission. A downstream gate that needs the missing fact still stops unless the existing body or an Accepted design answers it explicitly.
- COMMENT, acceptance-checkbox, and metadata-only mutations do not force format migration.
- The first `contractAffecting` mutation to a legacy-compatible Issue must upgrade it to the current minimum contract in the same preview.
- Do not bulk-migrate, silently rewrite, or lift a frozen-body constraint. Each Issue mutation retains its own preview and authorization boundary.

Compatibility status controls mutation admission; it is not a canonicalization version or fingerprint input.

## Supported actions

```text
CREATE
UPDATE
COMMENT
SET_LABELS
SET_MILESTONE
SET_ASSIGNEES
SET_RELATIONSHIP
CLOSE
REOPEN
```

Treat all of these as variants of one governed mutation workflow, not separate skills.

## Classify mutation impact

Before previewing a body or relationship mutation, classify every changed meaning:

- `framingAffecting`: changes why the work exists or reverses material problem evidence;
- `contractAffecting`: changes the delivery target, Acceptance Criteria semantics or verification authority, direct dependencies, Non-goals, or constraints;
- `designAffecting`: changes architecture impact or the Accepted design reference;
- `acceptanceEvidence`: changes criterion completion or its evidence without changing the criterion;
- `historyOnly`: appends rationale, progress, investigation, or prior decision evidence;
- `metadataOnly`: changes Provider metadata that the repository does not define as contract-bearing.

A mutation may have more than one class. When classification is ambiguous and the less disruptive interpretation could preserve an invalid authorization or Review, stop with `unknown` instead of guessing.

## Mutation plan

Use this logical structure; adapting presentation is allowed, but do not omit authority, concurrency, downstream impact, or authorization fields:

```text
IssueMutationPlan
├── action
├── repository
├── issueNumber?
├── expectedUpdatedAt?
├── repositoryPolicySource
├── issueContractStatus
├── rationale
├── exactWrites[]
├── impactClasses[]
├── invalidatedEvidence[]
├── requiredNextGates[]
└── requiredAuthorization
```

Creating an Issue and then adding a Parent, dependency, label, or comment is a multi-write plan. The preview, authorization, execution, and verification must cover every write.

## Mutation workflow

1. Resolve the exact GitHub host, `owner/repository`, and Issue number, or confirm that CREATE has no Issue yet. Never rely on the current directory alone when the target is ambiguous.
2. Before CREATE, search both existing Issues, including closed Issues, and the codebase for duplicate or already delivered work.
3. Refresh facts required by the selected mutation path. For the full path, include title, body, state, labels or native type, Milestone, assignees, `updatedAt`, URL, Parent/Sub-issues, and direct dependencies. Do not treat a skipped unrelated lookup as an empty fact.
4. Load the applicable repository policy. For CREATE or body/relationship changes, classify the current Issue as `current`, `legacy-compatible`, `unknown`, or `conflicting`; a history-only comment does not require whole-Issue classification.
5. Parse the meaning being changed by evidence role. Preserve unknown values and conflicts between native relationships and body fallbacks. Require a current-contract upgrade in the same preview when a legacy-compatible Issue receives a `contractAffecting` mutation; do not force it for history-only or metadata-only actions.
6. Classify semantic differences and determine which challenge verdict, decision record, implementation-gate receipt, authorization, or Review may be stale.
7. Prepare the exact user-visible writes and downstream consequences: use a semantic body diff for edits and complete rendered Markdown for CREATE or COMMENT. Show them before requesting authorization; reference an already presented identical plan rather than displaying it again solely for confirmation.
8. Check existing explicit authorization for the exact target, action, content, and scope. If that plan was already shown and approved, proceed without another confirmation. Otherwise present the concrete plan and obtain authorization. A discussion conclusion, recommendation, gate verdict, development brief, or permission for a different mutation is not authorization.
9. Immediately refresh the target again. A changed `updatedAt` triggers a comparison, not automatic loss of authorization. If relevant content, overwritten fields, contract, state, relationships, or impact changed, regenerate the plan and obtain authorization for any materially changed writes or consequences. If only unrelated activity changed and the approved plan remains identical and valid, record why and continue. Never apply an old whole-body replacement over concurrent edits or treat a failed comparison as unchanged. This preflight is not an atomic compare-and-swap; preserve any provider conflict and verify after writing.
10. Execute only the authorized mutation. Use `gh issue` for supported Issue fields and `gh api` for native relationship operations. Pass multiline bodies through stdin or `--body-file -`; never interpolate untrusted Markdown into a shell command.
11. Read GitHub again and compare the result with the plan. Report partial application, unresolved invalidation, and original failures explicitly; never claim success from a zero exit code alone.

Authorization must still be in force, not revoked or narrowed. It covers the intended write once, not repeated publication. Before retrying an uncertain mutation, read back whether it already took effect; do not blindly replay it or interpret a failed lookup as absence. If the outcome remains unknown, report it and stop the retry.

## Body versus comment

Update the body when the current contract or stable framing/design information changes. Add a comment for append-only history such as rationale, progress, blockers, investigation, execution evidence, risks, or next action.

A comment does not redefine the contract. If a comment records an accepted requirement or decision change, propose a separate body update and classify its downstream impact before delivery consumes it.

## Review and completion evidence — when the mutation depends on it

- An Agent completion statement, commit creation, or test pass is not completion evidence.
- A Review verdict binds the exact PR head; a changed head requires another Review.
- Where the repository defines a canonical contract fingerprint, a Review also binds it. This Skill does not invent that scheme or require one for repositories that have none.
- If a required repository contract schema or canonicalization version cannot be interpreted, report `unknown` and do not preserve the dependent authorization or Review as current. Unrelated history-only comments do not acquire that dependency.
- Close a delivery Issue only after verifying its PR, exact head, independent Review, Acceptance Criteria, required external evidence, and repository closing gates.

## Hard boundaries

- Do not write to GitHub without explicit authorization for the exact mutation.
- Do not create, close, reopen, reclassify, or relate Issues merely because an Agent recommends it.
- Do not overwrite concurrent GitHub edits.
- Do not treat local configuration, an Agent transcript, or a ledger as a competing source of GitHub truth.
- Do not expose tokens, secrets, sensitive private evidence, or raw private transcripts in previews, commands, comments, or bodies.
- Do not implement code, approve or merge a PR, deploy, or perform production writes under this Skill.
