import subprocess

from packaging.version import Version
from support import write

from repo_audit.release import Release, ReleaseTags


def git(repo, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


def release(repo, tag: str, speckit: str) -> None:
    write(repo / "extension.yml", f"requires:\n  speckit_version: '>={speckit}'\n")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", tag)
    git(repo, "tag", tag)


def test_latest_is_the_highest_version_not_the_last_in_text_order(tmp_path):
    git(tmp_path, "init", "-q")
    release(tmp_path, "v1.10.0", "0.9.0")
    release(tmp_path, "v1.9.0", "0.8.0")
    assert ReleaseTags(tmp_path).latest() == Release(
        "v1.10.0", Version("1.10.0"), Version("0.9.0")
    )
