"""The Markdown report of the audit."""

from dataclasses import dataclass
from datetime import date

from repo_audit.release import Release
from repo_audit.state import EXTENSION_ID, RepoState


@dataclass(frozen=True)
class Table:
    """A Markdown table of repos, with or without why each one is behind."""

    repos: list[RepoState]
    release: Release
    with_status: bool

    def lines(self) -> list[str]:
        header = "| Repo | Spec Kit | `opsmill` | Other extensions and presets |"
        rule = "| --- | --- | --- | --- |"
        if self.with_status:
            header, rule = header + " Behind because |", rule + " --- |"
        return [header, rule, *(self.row(repo) for repo in self.repos)]

    def row(self, repo: RepoState) -> str:
        row = (
            f"| [{repo.name}]({repo.url}) | {repo.speckit or 'not recorded'} "
            f"| {repo.extensions.get(EXTENSION_ID, 'none')} | {repo.components()} |"
        )
        if self.with_status:
            row += f" {'; '.join(repo.behind(self.release)) or 'up to date'} |"
        return row


@dataclass(frozen=True)
class Report:
    """The repos in scope first, then every other repo that uses Spec Kit."""

    repos: list[RepoState]
    release: Release
    in_scope: list[str]
    today: date

    def text(self) -> str:
        scoped = self.scoped()
        behind = [repo for repo in scoped if repo.behind(self.release)]
        others = [repo for repo in self.repos if repo.name not in self.in_scope]
        lines = [
            (
                f"{len(behind)} of {len(scoped)} repos in scope are behind {self.release.tag}, "
                f"the latest opsmill-speckit release (Spec Kit {self.release.min_speckit} or later)."
            ),
            "",
            (
                f"Read on {self.today.isoformat()} from the default branch of each repo, "
                "in `.specify/init-options.json` and the extension and preset registries."
            ),
            "",
            "## Repos in scope",
            "",
            *Table(scoped, self.release, with_status=True).lines(),
            "",
            "## Other repos with a `.specify/` directory",
            "",
            "Not in the migration scope. Their owners can install the latest release when they choose.",
            "",
            *Table(others, self.release, with_status=False).lines(),
        ]
        return "\n".join(lines) + "\n"

    def scoped(self) -> list[RepoState]:
        """The repos in scope, including those without Spec Kit."""
        by_name = {repo.name: repo for repo in self.repos}
        return [
            by_name.get(name) or RepoState(name, f"https://github.com/{name}", None)
            for name in self.in_scope
        ]
