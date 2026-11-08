import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

SOURCE = Path(__file__).resolve().parents[4] / "scripts"
SCRIPTS = Path(".specify/extensions/opsmill/scripts/bash")


def git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def clean_env() -> dict[str, str]:
    return {
        key: value
        for key, value in os.environ.items()
        if key not in ("SPECKIT_PYTHON_EXECUTABLE", "SPECKIT_PYTHON", "UV_PROJECT_ENVIRONMENT")
        and not key.startswith("GIT_")
    }


@pytest.fixture
def checkouts(tmp_path: Path) -> tuple[Path, Path]:
    """A main checkout whose environment has PyYAML, and a linked worktree without an environment."""
    main = tmp_path / "main checkout"
    shutil.copytree(SOURCE, main / ".specify/extensions/opsmill/scripts")
    git(main, "init", "-q")
    git(main, "add", ".")
    git(main, "-c", "user.name=test", "-c", "user.email=test@example.com", "commit", "-q", "-m", "init")
    (main / ".venv").symlink_to(sys.prefix)
    worktree = tmp_path / "linked worktree"
    git(main, "worktree", "add", "-q", "--detach", str(worktree))
    return main.resolve(), worktree.resolve()


def session_start_python(project: Path, tmp_path: Path) -> str:
    """Return the interpreter that a shell sourcing the session's environment file points spec-kit at."""
    env_file = tmp_path / "claude-env"
    env_file.write_text("")
    subprocess.run(
        [str(project / SCRIPTS / "python-env.sh")],
        cwd=project,
        env={**clean_env(), "CLAUDE_ENV_FILE": str(env_file), "CLAUDE_PROJECT_DIR": str(project)},
        check=True,
    )
    return subprocess.run(
        ["sh", "-c", '. "$1" && printf %s "${SPECKIT_PYTHON_EXECUTABLE:-}"', "sh", str(env_file)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def codex_python(project: Path) -> str:
    """Return the interpreter that the Codex wrapper points spec-kit at."""
    return subprocess.run(
        [str(project / SCRIPTS / "python-run.sh"), 'printf %s "${SPECKIT_PYTHON_EXECUTABLE:-}"'],
        cwd=project,
        env=clean_env(),
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def test_session_start_uses_the_main_checkout_environment_in_a_worktree_without_one(checkouts, tmp_path):
    main, worktree = checkouts
    assert session_start_python(worktree, tmp_path) == str(main / ".venv/bin/python")


def test_codex_wrapper_uses_the_main_checkout_environment_in_a_worktree_without_one(checkouts):
    main, worktree = checkouts
    assert codex_python(worktree) == str(main / ".venv/bin/python")


def test_worktree_environment_comes_before_the_main_checkout_one(checkouts, tmp_path):
    _, worktree = checkouts
    (worktree / ".venv").symlink_to(sys.prefix)
    assert session_start_python(worktree, tmp_path) == str(worktree / ".venv/bin/python")
    assert codex_python(worktree) == str(worktree / ".venv/bin/python")


def test_nothing_is_set_when_no_environment_has_pyyaml(checkouts, tmp_path):
    main, worktree = checkouts
    (main / ".venv").unlink()
    assert session_start_python(worktree, tmp_path) == ""
    assert codex_python(worktree) == ""
