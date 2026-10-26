from dataclasses import dataclass

from repo_audit.github import Organization


@dataclass(frozen=True)
class FakeGraphQL:
    """Two pages of repos; only the second one uses Spec Kit."""

    def query(self, query: str, **variables: str) -> dict:
        if "after" not in variables:
            nodes, info = (
                [{"nameWithOwner": "o/a"}],
                {"hasNextPage": True, "endCursor": "c1"},
            )
        else:
            nodes = [
                {
                    "nameWithOwner": "o/b",
                    "url": "u",
                    "specify_dir": {"__typename": "Tree"},
                }
            ]
            info = {"hasNextPage": False, "endCursor": None}
        return {
            "data": {
                "organization": {"repositories": {"nodes": nodes, "pageInfo": info}}
            }
        }


def test_reads_every_page_of_repos():
    assert [repo.name for repo in Organization("o", FakeGraphQL())] == ["o/b"]
