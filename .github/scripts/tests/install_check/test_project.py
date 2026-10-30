import pytest
from support import write

from install_check.errors import CheckFailed
from install_check.project import AgentFile, Specify


class TestSpecify:
    def test_fails_with_the_command_and_its_exit_code(self, tmp_path):
        with pytest.raises(CheckFailed, match="false init exited with 1"):
            Specify(("false",)).run(tmp_path, "init")


class TestAgentFile:
    def test_ignores_spec_kit_own_copies(self, project):
        write(project.path / ".specify" / "presets" / "a" / "speckit.plan.md", "")
        with pytest.raises(CheckFailed, match="speckit.plan: no skill or command file"):
            AgentFile(project, "speckit.plan").path()
