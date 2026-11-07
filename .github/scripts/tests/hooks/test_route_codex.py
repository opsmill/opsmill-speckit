import json
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[4] / "scripts"
CORE_SCRIPTS = ("setup-plan", "setup-tasks", "resolve-template", "create-new-feature")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A project with the opsmill hooks installed, at a path that holds a space and parentheses."""
    root = tmp_path / "checkout (copy)"
    scripts = root / ".specify" / "extensions" / "opsmill" / "scripts"
    shutil.copytree(SOURCE, scripts)
    core = root / ".specify" / "scripts" / "bash"
    core.mkdir(parents=True)
    for name in CORE_SCRIPTS:
        (core / f"{name}.sh").write_text("#!/usr/bin/env bash\n")
    (root / "dev").mkdir()
    return root.resolve()


def route(repo: Path, command: str, cwd: Path | None = None, tool_name: str = "Bash") -> str | None:
    """Return the command the hook asks Codex to run instead, or None when it leaves it alone."""
    hook_input = {"tool_name": tool_name, "cwd": str(cwd or repo), "tool_input": {"command": command}}
    result = subprocess.run(
        [sys.executable, str(repo / ".specify/extensions/opsmill/scripts/python/route_codex.py")],
        input=json.dumps(hook_input),
        capture_output=True,
        text=True,
        check=True,
        timeout=5,
    )
    if not result.stdout.strip():
        return None
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["permissionDecision"] == "allow"
    return output["updatedInput"]["command"]


@pytest.mark.parametrize(
    "command",
    [
        ".specify/scripts/bash/setup-plan.sh --json",
        "bash .specify/scripts/bash/setup-tasks.sh --json",
        ".specify/scripts/bash/resolve-template.sh constitution-template --json",
        ".specify/scripts/bash/create-new-feature.sh --json --short-name x",
        "'.specify/scripts/bash/setup-plan.sh' --json",
        '"{repo}/.specify/scripts/bash/setup-plan.sh" --json',
        "'{repo}/.specify/scripts/bash/setup-plan.sh' --json",
    ],
)
def test_reroutes_one_call_of_a_script_that_needs_pyyaml(repo, command):
    command = command.format(repo=repo)
    wrapper = repo / ".specify/extensions/opsmill/scripts/bash/python-run.sh"
    assert route(repo, command) == f"{shlex.quote(str(wrapper))} {shlex.quote(command)}"


@pytest.mark.parametrize(
    "command",
    [
        "ls -la",
        ".specify/scripts/bash/check-prerequisites.sh --json",
        ".specify/scripts/bash/setup-plan.sh.bak",
        "cat notes/setup-plan.sh",
        ".specify/extensions/git/scripts/bash/create-new-feature.sh --json",
        # A rewritten command runs without approval, so anything beyond the one call is left alone.
        "cd {repo} && .specify/scripts/bash/setup-plan.sh --json",
        ".specify/scripts/bash/setup-plan.sh --json; rm -rf x",
        ".specify/scripts/bash/setup-plan.sh --json | tee out",
        "OUT=$(.specify/scripts/bash/setup-plan.sh --json)",
        "FOO=1 .specify/scripts/bash/setup-plan.sh --json",
        "A+=x/../.specify/scripts/bash/setup-plan.sh echo x",
        "A=1\r.specify/scripts/bash/setup-plan.sh echo x",
        ".specify/scripts/bash/setup-plan.sh 'a b'",
        ".specify/scripts/bash/setup-plan.sh $(id)",
        'git commit -m "route (.specify/scripts/bash/setup-plan.sh)"',
        "echo 'a; .specify/scripts/bash/setup-plan.sh'",
        "cat <<EOF\n.specify/scripts/bash/setup-plan.sh\nEOF",
        # The script must be the one of this checkout.
        "/tmp/other/.specify/scripts/bash/setup-plan.sh --json",
        "{repo}/x/../.specify/scripts/bash/setup-plan.sh --json",
        '"{repo}/x$(id)/.specify/scripts/bash/setup-plan.sh"',
        '"{repo}/x`id`/.specify/scripts/bash/setup-plan.sh"',
        "{repo}/.specify/scripts/bash/setup-plan.sh --json",
    ],
)
def test_leaves_other_commands_alone(repo, command):
    assert route(repo, command.format(repo=repo)) is None


def test_leaves_a_relative_call_from_another_directory_alone(repo):
    assert route(repo, ".specify/scripts/bash/setup-plan.sh --json", cwd=repo / "dev") is None


def test_leaves_other_tools_alone(repo):
    assert route(repo, ".specify/scripts/bash/setup-plan.sh --json", tool_name="Read") is None


def test_does_not_wrap_twice(repo):
    wrapped = route(repo, ".specify/scripts/bash/setup-plan.sh --json")
    assert wrapped is not None
    assert route(repo, wrapped) is None


def test_answers_quickly_on_a_long_run_of_dollar_words(repo):
    assert route(repo, "$aaaaaaaa" * 40 + "/.specify/scripts/bash/setup-plan.sh") is None
