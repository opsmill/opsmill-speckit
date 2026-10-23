"""What a repo has installed, compared with a release."""

from dataclasses import dataclass, field

from packaging.version import InvalidVersion, Version

from repo_audit.release import Release

EXTENSION_ID = "opsmill"


@dataclass(frozen=True)
class InstalledVersion:
    """A version a repo records; one that cannot be read counts as outdated."""

    text: str

    def older_than(self, expected: Version) -> bool:
        try:
            return Version(self.text) < expected
        except InvalidVersion:
            return True


@dataclass(frozen=True)
class RepoState:
    """The Spec Kit version and components installed in a repo."""

    name: str
    url: str
    speckit: str | None
    extensions: dict[str, str] = field(default_factory=dict)
    presets: dict[str, str] = field(default_factory=dict)

    def behind(self, release: Release) -> list[str]:
        """Why the repo is behind the release; empty when it is up to date."""
        reasons = []
        installed = self.extensions.get(EXTENSION_ID)
        if installed is None:
            reasons.append(f"`{EXTENSION_ID}` not installed")
        elif InstalledVersion(installed).older_than(release.version):
            reasons.append(f"`{EXTENSION_ID}` {installed}, latest is {release.version}")
        if self.speckit is None:
            reasons.append("Spec Kit version not recorded")
        elif InstalledVersion(self.speckit).older_than(release.min_speckit):
            reasons.append(
                f"Spec Kit {self.speckit}, {release.tag} needs {release.min_speckit} or later"
            )
        return reasons

    def components(self) -> str:
        """The other extensions and the presets, as one line."""
        items = [
            f"{k} {v}" for k, v in sorted(self.extensions.items()) if k != EXTENSION_ID
        ]
        items += [f"{k} {v} (preset)" for k, v in sorted(self.presets.items())]
        return ", ".join(items) or "none"
