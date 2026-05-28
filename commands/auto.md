---
description: Run the full speckit workflow end-to-end — specify, plan, critique, tasks, implement, review — making all decisions autonomously. Stops before extract; run that manually.
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

You are running the **full speckit pipeline** end-to-end. The user's input (above) is the feature description that will seed the specification phase.

This skill is a thin orchestrator over two sibling skills:

- `speckit-opsmill-prep` — Specify → Plan → Critique → Tasks (+ spec/ask alignment check)
- `speckit-opsmill-implement` — Implement → Review → Final report

Run them back-to-back, making all decisions autonomously. Do not stop to ask the user for input between phases — if a sub-phase requires choices (clarification questions in specify, research decisions in plan, drift remediation in alignment), use your best judgment and proceed. The user expects a hands-off, one-shot execution. Extraction (`speckit-opsmill-extract`) is **not** run by this command — the user invokes it manually after reviewing the implementation report.

> Each phase below is executed by invoking the named skill (e.g. via the agent's Skill tool). Skills are agent-agnostic, so this workflow runs identically across any harness that supports skill discovery — not only those exposing speckit slash commands.

### Phase A — Preparation (delegated to `speckit.auto.prep`)

Invoke the `speckit-opsmill-prep` skill with the user's feature description (`$ARGUMENTS`) verbatim.

- This covers Specify → Plan → Critique → Tasks **and** the trailing spec/ask alignment check.
- The sub-skill commits its own artifacts after each phase via `speckit-checkpoint-commit`.
- If the alignment check inside auto-prep loops (re-running plan/critique/tasks to fix spec drift), let it run to completion. Do not interfere.
- Capture the spec directory path it produced — you will pass it to Phase B.

If `speckit-opsmill-prep` reports it stopped early (e.g., alignment never converged within its retry budget), surface the failure to the user and stop. Do not proceed to implementation on a misaligned spec.

### Phase B — Implementation tail (delegated to `speckit-opsmill-implement`)

Invoke the `speckit-opsmill-implement` skill with the spec directory path from Phase A as its argument.

- This covers Phase 0 (Preflight) → Phase 5 (Implement loop in clean-context subagents) → Phase 6 (Review) → Phase 7 (Final report).
- The sub-skill writes `<spec-dir>/opsmill-implement-report.md` and commits it.
- If it reports blocked tasks or unfixed high-severity review findings, capture that for the final summary — but do not retry from this orchestrator. The user will decide whether to re-run.

## Completion

After both phases are complete, provide a brief summary:

- Feature name and spec directory
- Whether the alignment check inside auto-prep required retries (and how many)
- Number of tasks completed (from the auto-implement report)
- Any review findings that were fixed inline vs. deferred
- Any notable decisions you or the sub-skills made autonomously

Do **not** open a PR, push, run extraction, or start a new feature. The user takes it from there — extraction (`/speckit.opsmill.extract`) is intentionally left as a manual follow-up so the user can review the implementation report first.
