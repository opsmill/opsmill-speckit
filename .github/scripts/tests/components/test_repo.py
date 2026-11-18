import subprocess

from support import write

from repo.files import Snapshot


class TestSnapshot:
    def test_lists_tracked_and_unignored_files_only(self, tmp_path):
        repo = tmp_path / "repo"
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        write(repo / ".gitignore", "ignored.txt\n")
        write(repo / "tracked" / "a.md", "a")
        write(repo / "untracked.md", "b")
        write(repo / "ignored.txt", "c")
        subprocess.run(["git", "-C", str(repo), "add", "tracked"], check=True)

        assert Snapshot(repo).files() == [
            ".gitignore",
            "tracked/a.md",
            "untracked.md",
        ]
