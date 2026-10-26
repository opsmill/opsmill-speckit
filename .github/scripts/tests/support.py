from pathlib import Path


def write(path: Path, text: str) -> Path:
    """Write a file, creating its directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path
