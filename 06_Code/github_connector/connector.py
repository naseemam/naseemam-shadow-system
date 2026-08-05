from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import os

from document_library.service import DocumentCatalogEntry, DocumentLibraryService


@dataclass
class GitHubConnector:
    client: Any
    owner: str
    repo: str
    library: Optional[DocumentLibraryService] = None
    read_only: bool = True

    def __post_init__(self) -> None:
        if self.library is None:
            self.library = DocumentLibraryService()

    def discover_repository(self) -> DocumentCatalogEntry:
        payload = self.client.get_repository(self.owner, self.repo)
        entry = self._normalize_to_entry(
            title=f"{payload.get('full_name', f'{self.owner}/{self.repo}')}",
            content=payload.get("description", ""),
            category="repository",
            source="github",
            source_type="repository",
            url=payload.get("html_url", ""),
            branch=None,
            commit_sha=None,
            timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            approval_status="trusted",
            tags=["github", "repository"],
        )
        self.library._catalog.append(entry)
        self.library._documents[entry.document_id] = entry
        return entry

    def retrieve_branches(self) -> List[DocumentCatalogEntry]:
        payload = self.client.list_branches(self.owner, self.repo)
        entries = []
        for branch in payload or []:
            entry = self._normalize_to_entry(
                title=f"Branch {branch.get('name', 'unknown')}",
                content=f"Branch {branch.get('name', 'unknown')}",
                category="branch",
                source="github",
                source_type="branch",
                url="",
                branch=branch.get("name"),
                commit_sha=branch.get("commit", {}).get("sha"),
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                approval_status="trusted",
                tags=["github", "branch"],
            )
            entries.append(entry)
            self._register_entry(entry)
        return entries

    def retrieve_pull_requests(self) -> List[DocumentCatalogEntry]:
        payload = self.client.list_pull_requests(self.owner, self.repo)
        entries = []
        for pr in payload or []:
            entry = self._normalize_to_entry(
                title=f"PR #{pr.get('number', 0)}: {pr.get('title', 'Untitled')}",
                content=f"State: {pr.get('state', 'unknown')} | Head: {pr.get('head', {}).get('ref', '')}",
                category="pull_request",
                source="github",
                source_type="pull_request",
                url=pr.get("html_url", ""),
                branch=pr.get("head", {}).get("ref"),
                commit_sha=pr.get("merge_commit_sha"),
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                approval_status="trusted",
                tags=["github", "pull_request"],
            )
            entries.append(entry)
            self._register_entry(entry)
        return entries

    def retrieve_issues(self) -> List[DocumentCatalogEntry]:
        payload = self.client.list_issues(self.owner, self.repo)
        entries = []
        for issue in payload or []:
            entry = self._normalize_to_entry(
                title=f"Issue #{issue.get('number', 0)}: {issue.get('title', 'Untitled')}",
                content=f"State: {issue.get('state', 'unknown')}",
                category="issue",
                source="github",
                source_type="issue",
                url=issue.get("html_url", ""),
                branch=None,
                commit_sha=None,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                approval_status="trusted",
                tags=["github", "issue"],
            )
            entries.append(entry)
            self._register_entry(entry)
        return entries

    def retrieve_releases(self) -> List[DocumentCatalogEntry]:
        payload = self.client.list_releases(self.owner, self.repo)
        entries = []
        for release in payload or []:
            entry = self._normalize_to_entry(
                title=f"Release {release.get('tag_name', 'unknown')}",
                content=release.get("name", ""),
                category="release",
                source="github",
                source_type="release",
                url=release.get("html_url", ""),
                branch=None,
                commit_sha=None,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                approval_status="trusted",
                tags=["github", "release"],
            )
            entries.append(entry)
            self._register_entry(entry)
        return entries

    def retrieve_tags(self) -> List[DocumentCatalogEntry]:
        payload = self.client.list_tags(self.owner, self.repo)
        entries = []
        for tag in payload or []:
            entry = self._normalize_to_entry(
                title=f"Tag {tag.get('name', 'unknown')}",
                content=f"Tag {tag.get('name', 'unknown')}",
                category="tag",
                source="github",
                source_type="tag",
                url="",
                branch=None,
                commit_sha=None,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                approval_status="trusted",
                tags=["github", "tag"],
            )
            entries.append(entry)
            self._register_entry(entry)
        return entries

    def retrieve_workflows(self) -> List[DocumentCatalogEntry]:
        payload = self.client.list_workflows(self.owner, self.repo)
        entries = []
        for workflow in payload or []:
            entry = self._normalize_to_entry(
                title=f"Workflow {workflow.get('name', 'unknown')}",
                content=f"State: {workflow.get('state', 'unknown')}",
                category="workflow",
                source="github",
                source_type="workflow",
                url=workflow.get("html_url", ""),
                branch=None,
                commit_sha=None,
                timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                approval_status="trusted",
                tags=["github", "workflow"],
            )
            entries.append(entry)
            self._register_entry(entry)
        return entries

    def _normalize_to_entry(
        self,
        title: str,
        content: str,
        category: str,
        source: str,
        source_type: str,
        url: str,
        branch: Optional[str],
        commit_sha: Optional[str],
        timestamp: str,
        approval_status: str,
        tags: List[str],
    ) -> DocumentCatalogEntry:
        if not isinstance(tags, list):
            tags = list(tags or [])
        entry = DocumentCatalogEntry(
            document_id=f"github:{self.owner}:{self.repo}:{category}:{title}",
            title=title,
            source=source,
            category=category,
            language="en",
            created_date=timestamp,
            imported_date=timestamp,
            approval_status=approval_status,
            confidence_score=0.95,
            tags=tags,
            content=self._decorate_with_provenance(content, url=url, branch=branch, commit_sha=commit_sha, timestamp=timestamp),
            source_type=source_type,
        )
        return entry

    def _decorate_with_provenance(self, content: str, url: str, branch: Optional[str], commit_sha: Optional[str], timestamp: str) -> str:
        provenance = [f"Repository: {self.owner}/{self.repo}"]
        if url:
            provenance.append(f"URL: {url}")
        if branch:
            provenance.append(f"Branch: {branch}")
        if commit_sha:
            provenance.append(f"Commit SHA: {commit_sha}")
        if timestamp:
            provenance.append(f"Timestamp: {timestamp}")
        return f"{content}\n\nProvenance: {' | '.join(provenance)}"

    def _register_entry(self, entry: DocumentCatalogEntry) -> None:
        if self.library is None:
            return
        self.library._catalog.append(entry)
        self.library._documents[entry.document_id] = entry
