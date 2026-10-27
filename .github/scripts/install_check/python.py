"""The Python that spec-kit's scripts run on a developer machine."""

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScriptPython:
    """A fresh Python environment holding only the packages a developer installs."""

    packages: tuple[str, ...]

    def create(self, dest: Path) -> Path:
        subprocess.run(["uv", "venv", "-q", str(dest)], check=True)
        python = dest / "bin" / "python"
        if self.packages:
            subprocess.run(
                ["uv", "pip", "install", "-q", "--python", str(python), *self.packages],
                check=True,
            )
        return python
