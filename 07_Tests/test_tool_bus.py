import os
import sys
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CODE_ROOT = os.path.join(ROOT, "06_Code")
if CODE_ROOT not in sys.path:
    sys.path.insert(0, CODE_ROOT)

from github_connector.connector import GitHubConnector
from tool_bus.bus import ExecutiveToolBus, ToolInvocation
from tool_bus.github_tool import GitHubTool

MODULE_PATH = os.path.join(CODE_ROOT, "executive_brain.py")
import importlib.util

SPEC = importlib.util.spec_from_file_location("executive_brain", MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules["executive_brain"] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain


class StubGitHubClient:
    def get_repository(self, owner, repo):
        return {"full_name": f"{owner}/{repo}", "description": "Demo repo", "html_url": "https://github.com/example/repo"}

    def list_pull_requests(self, owner, repo):
        return [{"number": 5, "title": "Improve onboarding", "state": "open", "html_url": "https://github.com/example/repo/pull/5", "head": {"ref": "feature/onboarding"}, "merge_commit_sha": "deadbeef"}]

    def list_releases(self, owner, repo):
        return [{"tag_name": "v1.0.0", "name": "Release 1", "html_url": "https://github.com/example/repo/releases/tag/v1.0.0"}]

    def list_workflows(self, owner, repo):
        return [{"name": "CI", "state": "active", "html_url": "https://github.com/example/repo/actions"}]

    def list_issues(self, owner, repo):
        return [{"number": 7, "title": "Tracking bug", "state": "open", "html_url": "https://github.com/example/repo/issues/7"}]

    def list_branches(self, owner, repo):
        return [{"name": "main", "commit": {"sha": "abc123"}}]

    def list_tags(self, owner, repo):
        return [{"name": "v1.0.0"}]


class ToolBusTests(unittest.TestCase):
    def test_connector_registration_and_routing(self):
        bus = ExecutiveToolBus()
        connector = GitHubConnector(client=StubGitHubClient(), owner="example", repo="repo")
        tool = GitHubTool(connector)
        bus.register_tool(tool)

        result = bus.route(ToolInvocation(capability="pull_request.list", payload={"owner": "example", "repo": "repo"}))

        self.assertTrue(result.success)
        self.assertEqual(result.tool_name, "github")
        self.assertEqual(result.data["entries"][0]["title"], "PR #5: Improve onboarding")

    def test_connector_isolation_and_brain_isolation(self):
        bus = ExecutiveToolBus()
        connector = GitHubConnector(client=StubGitHubClient(), owner="example", repo="repo")
        tool = GitHubTool(connector)
        bus.register_tool(tool)

        result = bus.route(ToolInvocation(capability="release.list", payload={"owner": "example", "repo": "repo"}))
        self.assertTrue(result.success)
        self.assertEqual(result.data["entries"][0]["title"], "Release v1.0.0")

        brain = ExecutiveBrain(normalize_fn=lambda x: x)
        plan = brain.think("What is the status of PR #5?", [], guardian_result={"status": "pass", "reason": ""})
        self.assertNotIn("github", plan.executive_message.lower())

    def test_github_plugin_compatibility(self):
        connector = GitHubConnector(client=StubGitHubClient(), owner="example", repo="repo")
        tool = GitHubTool(connector)
        self.assertTrue(tool.can_handle("pull_request.list"))
        self.assertTrue(tool.read_only)


if __name__ == "__main__":
    unittest.main()
