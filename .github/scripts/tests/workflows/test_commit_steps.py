"""The shell steps of the workflows that commit, run in a git repo as Spec Kit runs them."""

import subprocess
from pathlib import Path

import pytest
import yaml
from support import write

REPO = Path(__file__).resolve().parents[4]
RUNS = ".specify/workflows/runs"
WORKFLOWS = ("opsmill-prep", "opsmill-implement")


def shell_steps(steps: list) -> list[tuple[str, str]]:
    found = []
    for step in steps or []:
        if step.get("type") == "shell":
            found.append((step["id"], step["run"]))
        for key in ("steps", "then", "else"):
            found.extend(shell_steps(step.get(key)))
    return found


def steps_of(workflow: str) -> list[tuple[str, str]]:
    path = REPO / "workflows" / workflow / "workflow.yml"
    return shell_steps(yaml.safe_load(path.read_text())["steps"])


def commit_steps() -> list[tuple[str, str]]:
    return [
        (f"{workflow}.{step_id}", run)
        for workflow in WORKFLOWS
        for step_id, run in steps_of(workflow)
        if run.startswith("git add")
    ]


def guard(workflow: str) -> str:
    first_id, run = steps_of(workflow)[0]
    assert first_id == "runs-ignored"
    return run


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout


def run_in(repo: Path, script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", "-c", script], cwd=repo, capture_output=True, text=True
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    git(root, "config", "user.name", "test")
    git(root, "config", "user.email", "test@example.invalid")
    write(root / "README.md", "readme\n")
    git(root, "add", "README.md")
    git(root, "commit", "-q", "-m", "init")
    return root


def ignore_runs(repo: Path) -> None:
    write(repo / ".gitignore", f"{RUNS}/\n")
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-q", "-m", "ignore the runs")


def test_finds_the_commit_steps():
    assert len(commit_steps()) == 8


@pytest.mark.parametrize(
    ("step", "run"), commit_steps(), ids=[s for s, _ in commit_steps()]
)
def test_commits_the_work_and_leaves_out_the_ignored_run_state(repo, step, run):
    ignore_runs(repo)
    write(repo / RUNS / "abc123" / "state.json", "{}")
    write(repo / "specs" / "001-x" / "spec.md", "# Spec\n")

    result = run_in(repo, run)

    assert result.returncode == 0, result.stderr
    committed = git(repo, "show", "--name-only", "--format=", "HEAD").split()
    assert committed == ["specs/001-x/spec.md"]


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_stops_before_the_first_phase_when_the_run_state_is_not_ignored(repo, workflow):
    write(repo / RUNS / "abc123" / "state.json", "{}")

    result = run_in(repo, guard(workflow))

    assert result.returncode == 1
    assert result.stderr.startswith(
        "BLOCKED: add .specify/workflows/runs/ to the .gitignore"
    )


@pytest.mark.parametrize("workflow", WORKFLOWS)
def test_goes_on_when_the_run_state_is_ignored(repo, workflow):
    ignore_runs(repo)
    write(repo / RUNS / "abc123" / "state.json", "{}")

    assert run_in(repo, guard(workflow)).returncode == 0
