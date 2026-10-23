"""The repos of a GitHub organization, read through the GitHub API."""

import json
import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from typing import ClassVar

from repo_audit.state import RepoState


@dataclass(frozen=True)
class GraphQL:
    """The GitHub GraphQL API, called through the gh command line."""

    def query(self, query: str, **variables: str) -> dict:
        args = ["gh", "api", "graphql", "-f", f"query={query}"]
        for key, value in variables.items():
            args += ["-F", f"{key}={value}"]
        result = subprocess.run(args, check=True, capture_output=True, text=True)
        return json.loads(result.stdout)


@dataclass(frozen=True)
class Blob:
    """A JSON file read from a repo; a missing or unreadable file reads as empty."""

    node: dict
    key: str

    def json(self) -> dict:
        text = (self.node.get(self.key) or {}).get("text") or "{}"
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}


@dataclass(frozen=True)
class Organization:
    """The non-archived repos of an organization that use Spec Kit."""

    FILES: ClassVar[dict[str, str]] = {
        "specify_dir": ".specify",
        "init_options": ".specify/init-options.json",
        "extensions": ".specify/extensions/.registry",
        "presets": ".specify/presets/.registry",
    }
    QUERY: ClassVar[str] = """
query($org: String!, $after: String) {{
  organization(login: $org) {{
    repositories(first: 50, after: $after, isArchived: false, orderBy: {{field: NAME, direction: ASC}}) {{
      pageInfo {{ hasNextPage endCursor }}
      nodes {{ nameWithOwner url {fields} }}
    }}
  }}
}}
""".format(
        fields=" ".join(
            f'{key}: object(expression: "HEAD:{path}") {{ __typename ... on Blob {{ text }} }}'
            for key, path in FILES.items()
        )
    )

    login: str
    api: GraphQL

    def __iter__(self) -> Iterator[RepoState]:
        after = None
        while True:
            variables = {"org": self.login, **({"after": after} if after else {})}
            page = self.api.query(self.QUERY, **variables)["data"]["organization"][
                "repositories"
            ]
            for node in page["nodes"]:
                if node.get("specify_dir"):
                    yield self.state(node)
            if not page["pageInfo"]["hasNextPage"]:
                return
            after = page["pageInfo"]["endCursor"]

    def state(self, node: dict) -> RepoState:
        extensions = Blob(node, "extensions").json().get("extensions", {})
        presets = Blob(node, "presets").json().get("presets", {})
        return RepoState(
            name=node["nameWithOwner"],
            url=node["url"],
            speckit=Blob(node, "init_options").json().get("speckit_version"),
            extensions={k: str(v.get("version", "?")) for k, v in extensions.items()},
            presets={k: str(v.get("version", "?")) for k, v in presets.items()},
        )
