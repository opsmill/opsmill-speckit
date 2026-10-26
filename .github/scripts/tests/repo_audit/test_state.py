from packaging.version import Version

from repo_audit.release import Release
from repo_audit.state import RepoState

RELEASE = Release("v1.3.2", Version("1.3.2"), Version("0.8.0"))


def state(speckit: str, opsmill: str) -> RepoState:
    return RepoState("o/r", "https://github.com/o/r", speckit, {"opsmill": opsmill})


def test_a_repo_on_the_release_is_up_to_date():
    assert state("0.8.0", "1.3.2").behind(RELEASE) == []


def test_a_repo_on_an_older_spec_kit_is_behind():
    assert state("0.7.9", "1.3.2").behind(RELEASE) == [
        "Spec Kit 0.7.9, v1.3.2 needs 0.8.0 or later"
    ]


def test_an_unreadable_version_counts_as_behind():
    assert state("0.8.0", "main").behind(RELEASE) == ["`opsmill` main, latest is 1.3.2"]
