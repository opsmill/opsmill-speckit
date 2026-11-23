import subprocess

from support import write

from distribution.archives import build
from repo.components import Components


def repo_with_extension(root):
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    write(root / "extension.yml", "extension: {id: x, version: 1.0.0}\n")
    write(root / "commands" / "a.md", "a")
    write(root / "presets" / "p" / "preset.yml", "preset: {id: p, version: 1.0.0}\n")
    write(root / ".extensionignore", "presets/\n")
    return root


class TestArchives:
    def test_same_files_give_the_same_zip(self, tmp_path):
        repo = repo_with_extension(tmp_path / "repo")
        first = build(Components(repo), tmp_path / "first")
        (repo / "commands" / "a.md").touch()
        second = build(Components(repo), tmp_path / "second")
        assert [a.sha256() for a in first.values()] == [
            a.sha256() for a in second.values()
        ]

    def test_extension_zip_leaves_out_ignored_files(self, tmp_path):
        repo = repo_with_extension(tmp_path / "repo")
        extension = Components(repo).extension()
        assert sorted(extension.files()) == ["commands/a.md", "extension.yml"]

    def test_extension_zip_ignores_the_global_excludes(self, tmp_path, monkeypatch):
        repo = repo_with_extension(tmp_path / "repo")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        write(tmp_path / "excludes", "commands/\n")
        write(
            tmp_path / "gitconfig",
            f"[core]\n\texcludesFile = {tmp_path / 'excludes'}\n",
        )
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(tmp_path / "gitconfig"))
        extension = Components(repo).extension()
        assert sorted(extension.files()) == ["commands/a.md", "extension.yml"]
