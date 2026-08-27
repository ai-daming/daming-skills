---
name: challenge
description: Challenge the framing of a proposed coding task, plan, or product decision before execution. Use when the user asks to test whether the problem is real, expose weak assumptions, or find a higher-leverage alternative; do not use merely to manufacture objections.
---

# Challenge

Test the problem before optimizing the solution. The outcome is a justified recommendation to proceed, reframe, validate first, or stop—not criticism for its own sake.

## Invocation

Invoke with `$challenge` before planning or implementation when the framing itself is uncertain or the user asks for a hard stress test. This skill is not implementation authorization. If the framing is sound but material design decisions remain, recommend `$grill` as the next step.

Do not invoke just because a task is difficult, ordinary review is requested, or a harmless preference differs from yours.

## Workflow

1. **Set the boundary.** Restate the proposed action, intended outcome, affected users or systems, stated constraints, and what is outside this challenge. Flag ambiguity that could change the verdict.
2. **Establish reality.** Inspect available code, logs, data, documentation, and runtime state. Determine whether the claimed problem is observed, inferred, predicted, or merely assumed. Research discoverable facts yourself.
3. **Test the framing.** Ask whether the symptom is the real problem, whether the causal story is supported, who is materially affected, how often and how severely, what happens if nothing changes, and why action is needed now.
4. **Expose assumptions.** Separate facts, interpretations, constraints, and choices. Focus on assumptions whose failure would reverse the decision or invalidate the proposed solution.
5. **Search outside the frame.** Consider removing the root cause, changing the process or metric, narrowing scope, running a reversible experiment, reusing an existing capability, deferring, or doing nothing. Compare alternatives by impact, cost, reversibility, risk, and evidence gained.
6. **Give a verdict.** Recommend one of: **proceed**, **reframe**, **validate first**, or **stop**. Name the strongest reason, the evidence behind it, remaining uncertainty, and the smallest useful next step.

## Rules

- Challenge the highest-leverage premise first. Do not bury the verdict under minor objections.
- Be direct and specific, but use evidence rather than performative hostility.
- Do not invent a flaw to satisfy the tone of the request. Say when the framing is sound.
- Do not ask the user for facts available through repository or environment inspection. Ask only for preferences, priorities, authority, or genuinely unavailable context.
- Treat user-stated constraints as claims to understand, not automatically as immutable facts. Respect them once confirmed.
- Do not silently replace the user's goal with your preferred goal.
- Distinguish lack of evidence from evidence of absence.
- Preserve authorization boundaries. Analysis may recommend action; it does not authorize edits, external writes, deployment, or other mutations.
- Stop when further challenge would not materially change the verdict or next step.

## Output Style

Lead with the verdict, then provide only the material reasoning:

```markdown
## Verdict
Proceed | Reframe | Validate first | Stop

## Strongest challenge
<the premise most likely to change the decision, with evidence>

## Hidden assumptions
- <assumption> — <why it matters and how to test it>

## Higher-leverage alternatives
- <alternative> — <trade-off>

## Recommendation
<one concrete next step and any decision the user must make>
```

Omit empty sections. Calibrate depth to risk and reversibility rather than producing a fixed number of objections.

## Anti-patterns

- Contrarianism as a personality performance
- Nitpicking wording while accepting a broken causal model
- Treating speculation as observed fact
- Interrogating the user instead of inspecting available evidence
- Jumping into solution design before judging whether the problem deserves solving
- Listing many alternatives without ranking or recommending one
- Using “more research” as an indefinite escape hatch
- Continuing to attack a sound framing after the verdict is already stable
