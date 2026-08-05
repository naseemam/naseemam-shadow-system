import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CODE_ROOT = os.path.join(ROOT, '06_Code')
sys.path.insert(0, CODE_ROOT)

from document_library.service import DocumentLibraryService
from github_connector.connector import GitHubConnector

import importlib.util

MODULE_PATH = os.path.join(CODE_ROOT, 'executive_brain.py')
SPEC = importlib.util.spec_from_file_location('executive_brain', MODULE_PATH)
EXECUTIVE_BRAIN_MODULE = importlib.util.module_from_spec(SPEC)
sys.modules['executive_brain'] = EXECUTIVE_BRAIN_MODULE
assert SPEC.loader is not None
SPEC.loader.exec_module(EXECUTIVE_BRAIN_MODULE)
ExecutiveBrain = EXECUTIVE_BRAIN_MODULE.ExecutiveBrain

class StubGitHubClient:
    def get_repository(self, owner, repo):
        return {"full_name": f"{owner}/{repo}", "description": "Demo repo", "html_url": "https://github.com/example/repo"}
    def list_branches(self, owner, repo):
        return [{"name": "main", "commit": {"sha": "abc123"}}]
    def list_pull_requests(self, owner, repo):
        return [{"number": 5, "title": "Improve onboarding", "state": "open", "html_url": "https://github.com/example/repo/pull/5", "head": {"ref": "feature/onboarding"}, "merge_commit_sha": "deadbeef"}]
    def list_issues(self, owner, repo):
        return [{"number": 7, "title": "Tracking bug", "state": "open", "html_url": "https://github.com/example/repo/issues/7"}]
    def list_releases(self, owner, repo):
        return [{"tag_name": "v1.0.0", "name": "Release 1", "html_url": "https://github.com/example/repo/releases/tag/v1.0.0"}]
    def list_tags(self, owner, repo):
        return [{"name": "v1.0.0"}]
    def list_workflows(self, owner, repo):
        return [{"name": "CI", "state": "active", "html_url": "https://github.com/example/repo/actions"}]

client = StubGitHubClient()
connector = GitHubConnector(client=client, owner='example', repo='repo')
library = DocumentLibraryService()
library.attach_github_connector(connector)
results = library.search('What is the status of PR #5?')
print('RESULTS', [(r.title, r.content[:80]) for r in results])
print('CATALOG', [(r.title, r.content[:80]) for r in library.list_documents()])
brain = ExecutiveBrain(normalize_fn=lambda x: x, document_library=library)
plan = brain.think('What is the status of PR #5?', [], guardian_result={'status': 'pass', 'reason': ''})
print('CONTEXT', plan.context_summary)
