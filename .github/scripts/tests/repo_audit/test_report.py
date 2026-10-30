from datetime import date

from packaging.version import Version

from repo_audit.release import Release
from repo_audit.report import Report
from repo_audit.state import RepoState

RELEASE = Release("v1.3.2", Version("1.3.2"), Version("0.8.0"))


def test_tells_a_repo_the_token_cannot_read_from_one_without_spec_kit():
    without = RepoState("o/without", "u", None, uses_speckit=False)
    report = Report([without], RELEASE, ["o/hidden", "o/without"], date.today())
    hidden, without = report.scoped()
    assert hidden.behind(RELEASE) == ["not readable with the audit token"]
    assert "`opsmill` not installed" in without.behind(RELEASE)
