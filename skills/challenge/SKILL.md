---
name: challenge
description: Test whether a proposed problem, causal explanation, or direction is sound before committing to it. Use for uncertain framing or an explicit stress test, not routine difficulty or settled design choices.
---

# Challenge

Test the problem before optimizing the solution. Recommend `Proceed`, `Reframe`, `Validate first`, or `Stop` using evidence, not criticism for its own sake.

## When to run

Run when an unsupported premise could materially change the goal, scope, or decision to act, or when explicitly requested. Ordinary code review, a difficult implementation, and harmless preferences do not require Challenge.

Reuse accepted framing when its evidence, scope, and constraints still hold. Reopen it only for new material evidence, a contradiction, a scope change, or explicit user direction. If explicitly asked to challenge a sound framing, say why it holds and stop without manufacturing objections.

## Check the framing

1. Identify the intended outcome, affected users, fixed constraints, and out-of-scope work. Ask about the boundary only if competing interpretations change the verdict.
2. Inspect available code, logs, data, documentation, and runtime evidence. Separate observed facts, supported inferences, predictions, and assumptions. Reuse current evidence already gathered in the task; inspect anything missing or stale yourself.
3. Test the strongest premise: is the symptom the real problem, does the causal story hold, what is the impact, and what happens if nothing changes?
4. Consider credible alternatives that could improve the decision: removing the cause, reusing an existing capability, narrowing scope, a reversible experiment, deferring, or doing nothing. Rank the relevant alternatives; no fixed number is required.
5. Give the verdict, decisive evidence, remaining material uncertainty, and smallest useful next action. Stop when further challenge would not change that result.

## Boundaries

- Be direct and specific. Do not invent a flaw to match the user's tone.
- Ask only for user-owned priorities, authority, or genuinely unavailable context. Discoverable facts are the agent's work.
- Understand stated constraints and respect them once confirmed. Do not silently substitute your preferred goal.
- Lack of evidence is not evidence of absence. `Validate first` names a concrete missing observation, not indefinite research.
- A sound framing does not establish design completeness or implementation authority. Use `$grill` only if real user-owned choices remain, or `$impl-gate` when implementation readiness is the next question.
- `Proceed` needs no additional confirmation to continue analysis already authorized. Reframing a material goal needs user agreement; implementation and external actions retain their own authorization boundaries.

## Output

Lead with the verdict and the strongest reason. Include only material assumptions, credible alternatives, and the next action. A settled framing may need just a paragraph; use sections or examples only when they clarify a consequential decision. Refer to existing evidence rather than restating the upstream investigation.
