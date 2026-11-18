from support import write

from install_check.checks import HooksRegistered, Pinned
from install_check.components import BundleInstall, ExtensionInstall
from repo.components import Bundle, Extension

EXTENSION = """\
extension:
  id: opsmill
  version: 1.3.2
"""


class TestExtensionInstall:
    def test_checks_hooks_when_the_manifest_declares_some(self, tmp_path, project):
        hooks = "hooks:\n  after_tasks:\n    command: speckit.opsmill.summary\n"
        manifest = write(tmp_path / "src" / "extension.yml", EXTENSION + hooks)
        hooks_check = HooksRegistered(
            project, "opsmill", {"after_tasks": {"command": "speckit.opsmill.summary"}}
        )
        extension = Extension(tmp_path / "src", manifest)
        assert hooks_check in ExtensionInstall(extension).checks(project)


class TestBundleInstall:
    def test_checks_the_components_of_referenced_bundles(self, tmp_path, project):
        write(tmp_path / "extension.yml", EXTENSION)
        write(
            tmp_path / "bundles" / "base" / "bundle.yml",
            "bundle: {id: base}\n"
            "provides: {extensions: [{id: critique, version: 1.0.0, source: opsmill}]}\n",
        )
        jira = write(
            tmp_path / "bundles" / "jira" / "bundle.yml",
            "bundle: {id: jira}\n"
            "provides:\n"
            "  bundles: [{id: base, version: 1.0.0}]\n"
            "  extensions: [{id: git, version: 1.0.1}]\n",
        )
        assert BundleInstall(Bundle(tmp_path, jira)).checks(project) == [
            Pinned(project, "extensions", "critique", "1.0.0", True),
            Pinned(project, "extensions", "git", "1.0.1", False),
        ]
