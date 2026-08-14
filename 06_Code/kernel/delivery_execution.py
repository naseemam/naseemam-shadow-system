from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, Iterable, Optional
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from kernel.executive_kernel import ExecutiveKernel
from kernel.repository_execution import ControlledRepositoryPolicy


_GITHUB_API = "https://api.github.com"
_RAILWAY_API = "https://backboard.railway.com/graphql/v2"
_MAX_FILE_BYTES = 1_000_000


class DeliveryConfigurationError(RuntimeError):
    pass


class DeliveryRemoteError(RuntimeError):
    pass


class GitHubRepositoryClient:
    """Minimal GitHub delivery client used by Ameer at runtime.

    Authentication is deliberately read only from Railway environment variables.
    No token is ever written to disk or returned in command results.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.root = Path(workspace_root).resolve()
        self.token = (os.getenv("AMEER_GITHUB_TOKEN") or "").strip()
        owner = (os.getenv("AMEER_GITHUB_OWNER") or os.getenv("RAILWAY_GIT_REPO_OWNER") or "").strip()
        repo = (os.getenv("AMEER_GITHUB_REPO") or os.getenv("RAILWAY_GIT_REPO_NAME") or "").strip()
        explicit = (os.getenv("AMEER_GITHUB_REPOSITORY") or "").strip()
        if explicit and "/" in explicit:
            owner, repo = explicit.split("/", 1)
        self.owner = owner
        self.repo = repo
        self.base_branch = (os.getenv("AMEER_GITHUB_BASE_BRANCH") or "main").strip()
        self.delivery_branch = (os.getenv("AMEER_GITHUB_DELIVERY_BRANCH") or "ameer/automated-delivery").strip()
        self.policy = ControlledRepositoryPolicy(self.root)

    @property
    def configured(self) -> bool:
        return bool(self.token and self.owner and self.repo)

    def _require_configured(self) -> None:
        if not self.configured:
            raise DeliveryConfigurationError(
                "GitHub delivery requires AMEER_GITHUB_TOKEN and repository identity "
                "(AMEER_GITHUB_REPOSITORY or Railway Git variables)."
            )

    def _request(self, method: str, path: str, payload: Optional[dict] = None) -> Any:
        self._require_configured()
        url = f"{_GITHUB_API}{path}"
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = Request(
            url,
            data=data,
            method=method,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "Content-Type": "application/json",
                "User-Agent": "Ameer-Delivery-Agent",
            },
        )
        try:
            with urlopen(req, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DeliveryRemoteError(f"GitHub API {exc.code}: {detail[:800]}") from exc

    def _repo_path(self, suffix: str) -> str:
        return f"/repos/{quote(self.owner)}/{quote(self.repo)}{suffix}"

    def _get_ref(self, branch: str) -> Optional[dict]:
        try:
            return self._request("GET", self._repo_path(f"/git/ref/heads/{quote(branch, safe='')}") )
        except DeliveryRemoteError as exc:
            if "404" in str(exc):
                return None
            raise

    def _ensure_branch(self, branch: str, base_branch: str) -> dict:
        ref = self._get_ref(branch)
        if ref:
            return ref
        base_ref = self._get_ref(base_branch)
        if not base_ref:
            raise DeliveryRemoteError(f"Base branch not found: {base_branch}")
        base_sha = base_ref["object"]["sha"]
        return self._request(
            "POST",
            self._repo_path("/git/refs"),
            {"ref": f"refs/heads/{branch}", "sha": base_sha},
        )

    def _iter_delivery_files(self) -> Iterable[tuple[str, Path]]:
        for prefix in ("06_Code", "07_Tests", "09_Assets/web", "09_Assets/runtime_workspace"):
            root = self.root / prefix
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                rel = path.relative_to(self.root).as_posix()
                if not self.policy.is_allowed(rel):
                    continue
                if path.stat().st_size > _MAX_FILE_BYTES:
                    continue
                yield rel, path
        for name in ("ameer_server.py", "ameer_runtime.py", "start_ameer.py", "railway.toml", "requirements.txt"):
            path = self.root / name
            if path.is_file() and self.policy.is_allowed(name) and path.stat().st_size <= _MAX_FILE_BYTES:
                yield name, path

    def commit_and_push(
        self,
        *,
        message: str,
        branch: Optional[str] = None,
        base_branch: Optional[str] = None,
    ) -> Dict[str, Any]:
        branch = branch or self.delivery_branch
        base_branch = base_branch or self.base_branch
        ref = self._ensure_branch(branch, base_branch)
        parent_sha = ref["object"]["sha"]
        parent_commit = self._request("GET", self._repo_path(f"/git/commits/{parent_sha}"))
        base_tree = parent_commit["tree"]["sha"]

        tree_entries = []
        file_count = 0
        for rel, path in self._iter_delivery_files():
            content = path.read_bytes()
            blob = self._request(
                "POST",
                self._repo_path("/git/blobs"),
                {"content": base64.b64encode(content).decode("ascii"), "encoding": "base64"},
            )
            tree_entries.append({"path": rel, "mode": "100644", "type": "blob", "sha": blob["sha"]})
            file_count += 1

        if not tree_entries:
            return {"status": "no_files", "branch": branch, "commit_sha": parent_sha, "files": 0}

        tree = self._request(
            "POST",
            self._repo_path("/git/trees"),
            {"base_tree": base_tree, "tree": tree_entries},
        )
        if tree.get("sha") == base_tree:
            return {"status": "no_changes", "branch": branch, "commit_sha": parent_sha, "files": file_count}

        commit = self._request(
            "POST",
            self._repo_path("/git/commits"),
            {"message": message, "tree": tree["sha"], "parents": [parent_sha]},
        )
        commit_sha = commit["sha"]
        self._request(
            "PATCH",
            self._repo_path(f"/git/refs/heads/{quote(branch, safe='')}"),
            {"sha": commit_sha, "force": False},
        )
        return {"status": "pushed", "branch": branch, "commit_sha": commit_sha, "files": file_count}

    def create_pull_request(
        self,
        *,
        head: Optional[str] = None,
        base: Optional[str] = None,
        title: str = "Ameer automated delivery",
        body: str = "Changes prepared and pushed by Ameer under the controlled delivery policy.",
    ) -> Dict[str, Any]:
        head = head or self.delivery_branch
        base = base or self.base_branch
        query = urlencode({"state": "open", "head": f"{self.owner}:{head}", "base": base})
        existing = self._request("GET", self._repo_path(f"/pulls?{query}"))
        if isinstance(existing, list) and existing:
            pr = existing[0]
            return {"status": "existing", "number": pr["number"], "url": pr.get("html_url"), "head": head, "base": base}
        pr = self._request(
            "POST",
            self._repo_path("/pulls"),
            {"title": title, "head": head, "base": base, "body": body, "draft": False},
        )
        return {"status": "created", "number": pr["number"], "url": pr.get("html_url"), "head": head, "base": base}

    def merge_pull_request(self, number: int, method: str = "squash") -> Dict[str, Any]:
        merged = self._request(
            "PUT",
            self._repo_path(f"/pulls/{int(number)}/merge"),
            {"merge_method": method},
        )
        return {
            "status": "merged" if merged.get("merged") else "not_merged",
            "merged": bool(merged.get("merged")),
            "commit_sha": merged.get("sha"),
            "message": merged.get("message", ""),
            "pull_request": int(number),
        }


class RailwayDeploymentClient:
    """Railway Public API client scoped to the running service/environment."""

    def __init__(self) -> None:
        self.project_token = (os.getenv("AMEER_RAILWAY_PROJECT_TOKEN") or "").strip()
        self.account_token = (os.getenv("AMEER_RAILWAY_TOKEN") or "").strip()
        self.service_id = (os.getenv("RAILWAY_SERVICE_ID") or "").strip()
        self.environment_id = (os.getenv("RAILWAY_ENVIRONMENT_ID") or "").strip()
        self.project_id = (os.getenv("RAILWAY_PROJECT_ID") or "").strip()

    @property
    def configured(self) -> bool:
        return bool((self.project_token or self.account_token) and self.service_id and self.environment_id)

    def _graphql(self, query: str, variables: dict) -> dict:
        if not self.configured:
            raise DeliveryConfigurationError(
                "Railway delivery requires AMEER_RAILWAY_PROJECT_TOKEN (recommended) or "
                "AMEER_RAILWAY_TOKEN. Railway supplies service/environment/project IDs automatically."
            )
        headers = {"Content-Type": "application/json", "User-Agent": "Ameer-Delivery-Agent"}
        if self.project_token:
            headers["Project-Access-Token"] = self.project_token
        else:
            headers["Authorization"] = f"Bearer {self.account_token}"
        req = Request(
            _RAILWAY_API,
            data=json.dumps({"query": query, "variables": variables}).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise DeliveryRemoteError(f"Railway API {exc.code}: {detail[:800]}") from exc
        if payload.get("errors"):
            raise DeliveryRemoteError(f"Railway GraphQL error: {payload['errors'][:3]}")
        return payload.get("data") or {}

    def deploy(self, commit_sha: Optional[str] = None) -> Dict[str, Any]:
        mutation = """
        mutation AmeerDeploy($serviceId: String!, $environmentId: String!, $commitSha: String) {
          serviceInstanceDeployV2(serviceId: $serviceId, environmentId: $environmentId, commitSha: $commitSha)
        }
        """
        data = self._graphql(
            mutation,
            {"serviceId": self.service_id, "environmentId": self.environment_id, "commitSha": commit_sha},
        )
        deployment_id = data.get("serviceInstanceDeployV2")
        return {"status": "deployment_triggered", "deployment_id": deployment_id, "commit_sha": commit_sha}

    def deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        query = """
        query AmeerDeployment($id: String!) {
          deployment(id: $id) { id status createdAt }
        }
        """
        data = self._graphql(query, {"id": deployment_id})
        deployment = data.get("deployment") or {}
        return {
            "deployment_id": deployment.get("id", deployment_id),
            "status": deployment.get("status", "UNKNOWN"),
            "created_at": deployment.get("createdAt"),
        }

    def rollback(self, deployment_id: str) -> Dict[str, Any]:
        mutation = """
        mutation AmeerRollback($id: String!) {
          deploymentRollback(id: $id) { id }
        }
        """
        data = self._graphql(mutation, {"id": deployment_id})
        result = data.get("deploymentRollback") or {}
        return {"status": "rollback_triggered", "deployment_id": result.get("id", deployment_id)}


class DeliveryController:
    """Explicit external-effect commands for GitHub and Railway.

    These operations are never inferred from an ordinary build request. Ameer must
    see explicit delivery language such as push, merge, deploy, ship, or rollback.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        self.github = GitHubRepositoryClient(workspace_root)
        self.railway = RailwayDeploymentClient()

    def detect(self, command: str) -> Optional[str]:
        text = (command or "").strip().lower()
        if not text:
            return None
        if any(x in text for x in ("rollback", "تراجع عن النشر", "ارجع النشر", "استرجع النشر")):
            return "rollback"
        has_merge = any(x in text for x in ("merge", "ادمج", "إدمج", "دمج"))
        has_deploy = any(x in text for x in ("deploy", "انشر", "أنشر", "ريلوي", "railway", "production"))
        has_push = any(x in text for x in ("push", "ادفع", "إدفع", "ارفع للجيت", "ارفع إلى الجيت", "commit"))
        if has_merge and has_deploy:
            return "merge_and_deploy"
        if has_deploy:
            return "deploy"
        if has_merge:
            return "merge"
        if has_push:
            return "push"
        return None

    @staticmethod
    def _extract_number(command: str) -> Optional[int]:
        import re
        match = re.search(r"(?:#|pr\s*)?(\d+)", command or "", flags=re.IGNORECASE)
        return int(match.group(1)) if match else None

    def execute(self, action: str, command: str) -> Dict[str, Any]:
        started = time.time()
        try:
            if action == "push":
                pushed = self.github.commit_and_push(message=f"Ameer: {command[:120]}")
                pr = self.github.create_pull_request(head=pushed.get("branch")) if pushed.get("status") == "pushed" else None
                result = {"action": action, "github": pushed, "pull_request": pr}
            elif action == "merge":
                number = self._extract_number(command)
                if number is None:
                    pr = self.github.create_pull_request()
                    number = int(pr["number"])
                result = {"action": action, "github": self.github.merge_pull_request(number)}
            elif action == "deploy":
                commit_sha = (os.getenv("RAILWAY_GIT_COMMIT_SHA") or "").strip() or None
                result = {"action": action, "railway": self.railway.deploy(commit_sha=commit_sha)}
            elif action == "merge_and_deploy":
                number = self._extract_number(command)
                if number is None:
                    pushed = self.github.commit_and_push(message=f"Ameer delivery: {command[:100]}")
                    pr = self.github.create_pull_request(head=pushed.get("branch"))
                    number = int(pr["number"])
                merged = self.github.merge_pull_request(number)
                if not merged.get("merged"):
                    return {"status": "blocked", "reason": "pull_request_not_merged", "github": merged}
                deployment = self.railway.deploy(commit_sha=merged.get("commit_sha"))
                result = {"action": action, "github": merged, "railway": deployment}
            elif action == "rollback":
                deployment_id = (os.getenv("AMEER_ROLLBACK_DEPLOYMENT_ID") or "").strip()
                if not deployment_id:
                    raise DeliveryConfigurationError("Rollback requires AMEER_ROLLBACK_DEPLOYMENT_ID or a future explicit deployment-id parser.")
                result = {"action": action, "railway": self.railway.rollback(deployment_id)}
            else:
                return {"status": "ignored", "reason": "unknown_delivery_action", "action": action}
            result["status"] = "completed"
            result["duration_ms"] = int((time.time() - started) * 1000)
            return result
        except (DeliveryConfigurationError, DeliveryRemoteError, OSError, ValueError) as exc:
            return {
                "status": "blocked",
                "action": action,
                "reason": type(exc).__name__,
                "detail": str(exc),
                "duration_ms": int((time.time() - started) * 1000),
            }


class DeliveryExecutiveKernel(ExecutiveKernel):
    """ExecutiveKernel with an explicit external delivery lane."""

    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root)
        self.delivery = DeliveryController(workspace_root)

    def execute_command(self, command: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        action = self.delivery.detect(command)
        if action:
            return self.delivery.execute(action, command)
        return super().execute_command(command, *args, **kwargs)
