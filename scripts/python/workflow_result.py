#!/usr/bin/env python3
"""Print the result of a Spec Kit workflow run, for the command that started it.

Usage: workflow_result.py [RUN_ID]    (default: the most recent run of the project)

It prints the status of the run, how many times each agent phase started, the
verdict line that each phase ended with, and the reason of a run that stopped.
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

RUNS = Path(".specify/workflows/runs")
WORKFLOWS = Path(".specify/workflows")
# A line such as `ALIGNMENT: ALIGNED` or `STATUS: DONE | SPEC_DIR: ...`.
VERDICT = re.compile(r"^[A-Z][A-Z_]*: \S")
# What a stop step of a workflow prints before it ends the run.
STOP = re.compile(r"\b(?:BLOCKED|INCOMPLETE): [^'\"]*")


def last_line(text: object) -> str:
    lines = str(text or "").strip().splitlines()
    return lines[-1].strip() if lines else ""


def state_of(run_id: str | None) -> tuple[Path, dict]:
    states = (
        [RUNS / run_id / "state.json"] if run_id else list(RUNS.glob("*/state.json"))
    )
    states = [path for path in states if path.exists()]
    if not states:
        sys.exit(f"no workflow run found in {RUNS}")
    path = max(states, key=lambda path: path.stat().st_mtime)
    return path.parent, json.loads(path.read_text())


def phases(run: Path) -> Counter:
    """How many times each agent phase started, nested workflows included."""
    started: Counter = Counter()
    log = run / "log.jsonl"
    if not log.exists():
        return started
    for line in log.read_text().splitlines():
        event = json.loads(line)
        if event.get("event") == "step_started" and event.get("type") == "command":
            # A step of a repeated pass is named `design:critique:1`.
            names = [
                part
                for part in str(event.get("step_id", "")).split(":")
                if not part.isdigit()
            ]
            started[names[-1] if names else "?"] += 1
    return started


def verdicts(state: dict) -> list[str]:
    """The verdict line of each step, and of each output of a nested workflow."""
    lines = []
    for name, result in state.get("step_results", {}).items():
        output = result.get("output") or {}
        for key, value in output.items():
            if key in ("stderr", "error") or not isinstance(value, str):
                continue
            line = last_line(value)
            if VERDICT.match(line):
                lines.append(f"{name}{'' if key == 'stdout' else '.' + key} -> {line}")
    return lines


def stop_reasons(state: dict) -> list[str]:
    """Why the run stopped: what the stop step printed, or what its workflow file says it prints."""
    recorded = [
        match.group(0).strip()
        for result in state.get("step_results", {}).values()
        for match in STOP.finditer(
            str((result.get("output") or {}).get("stderr") or "")
        )
    ]
    step = state.get("current_step_id")
    if recorded or state.get("status") != "failed" or not step:
        return recorded
    # A nested workflow keeps the output of its steps to itself.
    for workflow in WORKFLOWS.glob("*/workflow.yml"):
        text = workflow.read_text()
        found = re.search(rf"^\s*- id: {re.escape(step)}\s*$", text, re.MULTILINE)
        if found:
            block = re.split(
                r"^\s*- id: ", text[found.end() :], maxsplit=1, flags=re.MULTILINE
            )[0]
            return [match.group(0).strip() for match in STOP.finditer(block)]
    return []


def main() -> int:
    run, state = state_of(sys.argv[1] if len(sys.argv) > 1 else None)
    print(
        f"run {state.get('run_id')} | workflow {state.get('workflow_id')} | {state.get('status')}"
    )
    started = phases(run)
    if started:
        print(
            "phases started: "
            + ", ".join(f"{name} x{count}" for name, count in started.items())
        )
    for line in verdicts(state):
        print(line)
    reasons = stop_reasons(state)
    for reason in reasons:
        print(reason if len(reasons) == 1 else f"possible reason: {reason}")
    if state.get("status") == "failed":
        print(f"failed at step {state.get('current_step_id')}: {state.get('error')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
