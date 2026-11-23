import json
import subprocess
import sys
from pathlib import Path

from support import write

SCRIPT = (
    Path(__file__).resolve().parents[4] / "scripts" / "python" / "workflow_result.py"
)


def run(project: Path, state: dict) -> str:
    """What the script prints for a project whose only run has this state."""
    write(project / ".specify/workflows/runs/r1/state.json", json.dumps(state))
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=project,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


class TestStopReason:
    def test_ends_at_the_end_of_its_line(self, tmp_path):
        state = {
            "status": "failed",
            "step_results": {
                "check-spec": {
                    "output": {
                        "stderr": "BLOCKED: the specify phase wrote no spec.md\n"
                        "Traceback (most recent call last):\n  File x\n"
                    }
                }
            },
        }
        output = run(tmp_path, state)
        assert "BLOCKED: the specify phase wrote no spec.md" in output.splitlines()
        assert "Traceback" not in output
