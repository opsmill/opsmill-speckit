import subprocess

import pytest
from build_release import published
from distribution.catalogs import Location


def git(*args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def clone(tmp_path):
    """A clone that lacks the tag v1.1.0, which its origin holds."""
    origin, clone = tmp_path / "origin", tmp_path / "clone"
    git("init", "-q", str(origin))
    git("-C", str(origin), "commit", "-q", "--allow-empty", "-m", "first")
    git("-C", str(origin), "tag", "v1.0.0")
    git("clone", "-q", str(origin), str(clone))
    git("-C", str(origin), "commit", "-q", "--allow-empty", "-m", "second")
    git("-C", str(origin), "tag", "v1.1.0")
    return clone


def test_a_release_tagged_only_on_origin_is_published(clone):
    assert published(clone) == (
        Location.release("1.0.0").archives,
        Location.release("1.1.0").archives,
    )


def test_fails_when_origin_cannot_be_read(clone, tmp_path):
    git("-C", str(clone), "remote", "set-url", "origin", str(tmp_path / "missing"))

    with pytest.raises(SystemExit, match="cannot list the tags of origin"):
        published(clone)
