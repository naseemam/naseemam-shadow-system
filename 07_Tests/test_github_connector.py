import os
import sys
import tempfile
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from document_library.service import DocumentLibraryService
from github_connector.connector import GitHubConnector

MODULE_PATH = os.path.join(CODE_ROOT, "executive_brain.py")
import importlib.util

SPEC = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["executive_brain"] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain


class StubGitHubClient:
    def __init__(self):
        self.calls = []

    def get_repository(self, owner, repo):
        self.calls.append(("repo", owner, repo))
        return {"full_name": f"{owner}/{repo}", "description": "Demo repo", "html_url": "https://github.com/example/repo"}

    def list_branches(self, owner, repo):
        self.calls.append(("branches", owner, repo))
        return [{"name": "main", "commit": {"sha": "abc123"}}]

    def list_pull_requests(self, owner, repo):
        self.calls.append(("prs", owner, repo))
        return [{"number": 5, "title": "Improve onboarding", "state": "open", "html_url": "https://github.com/example/repo/pull/5", "head": {"ref": "feature/onboarding"}, "merge_commit_sha": "deadbeef"}]

    def list_issues(self, owner, repo):
        self.calls.append(("issues", owner, repo))
        return [{"number": 7, "title": "Tracking bug", "state": "open", "html_url": "https://github.com/example/repo/issues/7"}]

    def list_releases(self, owner, repo):
        self.calls.append(("releases", owner, repo))
        return [{"tag_name": "v1.0.0", "name": "Release 1", "html_url": "https://github.com/example/repo/releases/tag/v1.0.0"}]

    def list_tags(self, owner, repo):
        self.calls.append(("tags", owner, repo))
        return [{"name": "v1.0.0"}]

    def list_workflows(self, owner, repo):
        self.calls.append(("workflows", owner, repo))
        return [{"name": "CI", "state": "active", "html_url": "https://github.com/example/repo/actions"}]


class GitHubConnectorTests(unittest.TestCase):
    def test_repository_discovery_and_pull_request_retrieval(self):
        client = StubGitHubClient()
        connector = GitHubConnector(client=client, owner="example", repo="repo")
        library = DocumentLibraryService()

        repo_entry = connector.discover_repository()
        pr_entries = connector.retrieve_pull_requests()

        self.assertEqual(repo_entry.title, "example/repo")
        self.assertEqual(pr_entries[0].title, "PR #5: Improve onboarding")
        self.assertEqual(len(client.calls), 2)

    def test_release_and_workflow_retrieval_are_read_only(self):
        client = StubGitHubClient()
        connector = GitHubConnector(client=client, owner="example", repo="repo")

        release_entries = connector.retrieve_releases()
        workflow_entries = connector.retrieve_workflows()

        self.assertEqual(release_entries[0].title, "Release v1.0.0")
        self.assertEqual(workflow_entries[0].title, "Workflow CI")
        self.assertEqual(release_entries[0].approval_status, "trusted")
        self.assertEqual(workflow_entries[0].approval_status, "trusted")

    def test_executive_brain_uses_document_library_for_github_queries(self):
        client = StubGitHubClient()
        connector = GitHubConnector(client=client, owner="example", repo="repo")
        library = DocumentLibraryService()
        library.attach_github_connector(connector)

        brain = ExecutiveBrain(normalize_fn=lambda x: x, document_library=library)
        plan = brain.think("What is the status of PR #5?", [], guardian_result={"status": "pass", "reason": ""})

        self.assertIn("PR #5", plan.context_summary)
        self.assertIn("prs", {call[0] for call in client.calls})
        self.assertGreaterEqual(len(library.list_documents()), 1)


if __name__ == "__main__":
    unittest.main()
