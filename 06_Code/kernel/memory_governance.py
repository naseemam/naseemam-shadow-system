"""
memory_governance.py
====================
P0.5 Memory & Knowledge Governance Engine.

يفرض فصل طبقات الذاكرة والمعرفة ويمنع أي كتابة مباشرة إلى Founder Memory
دون موافقة صريحة من المؤسسة.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from kernel.approval_gate import ApprovalGate


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class MemoryGovernanceEngine:
    CORE_IDENTITY = "core_identity"
    CORE_KNOWLEDGE = "core_knowledge"
    LEARNED_KNOWLEDGE = "learned_knowledge"
    FOUNDER_MEMORY = "founder_memory"
    WORKING_MEMORY = "working_memory"
    SESSION_MEMORY = "session_memory"

    LAYERS = {
        CORE_IDENTITY,
        CORE_KNOWLEDGE,
        LEARNED_KNOWLEDGE,
        FOUNDER_MEMORY,
        WORKING_MEMORY,
        SESSION_MEMORY,
    }

    _SENSITIVE_MARKERS = {
        "preferences": ["أفضل", "افضل", "prefer", "preference", "تفضيل"],
        "health": ["صحتي", "صحي", "health", "مرض", "دواء", "علاج"],
        "financial": ["مال", "راتب", "income", "budget", "financial", "استثمار", "دين"],
        "relationships": ["زوج", "زوجه", "علاقة", "relationship", "صديق", "صديقتي", "عائلتي"],
        "routine": ["روتيني", "routine", "daily", "يومي", "استيقظ", "انام", "sleep"],
    }

    def __init__(self, workspace_root: str | Path, approval_gate: ApprovalGate) -> None:
        self._root = Path(workspace_root).resolve()
        self._approval_gate = approval_gate
        self._dir = self._root / ".ameer"
        self._dir.mkdir(parents=True, exist_ok=True)

        self._founder_path = self._dir / "memory_founder.json"
        self._learned_path = self._dir / "memory_learned.json"
        self._working_path = self._dir / "memory_working.json"
        self._session_path = self._dir / "memory_session.json"
        self._pending_path = self._dir / "memory_candidates.json"
        self._governance_log_path = self._dir / "governance_log.json"
        self._core_promotions_path = self._dir / "core_knowledge_promotions.json"

        self._founder_items = self._load_list(self._founder_path)
        self._learned_items = self._load_list(self._learned_path)
        self._working_items = self._load_list(self._working_path)
        self._session_items = self._load_list(self._session_path)
        self._pending_candidates = self._load_list(self._pending_path)
        self._governance_log = self._load_list(self._governance_log_path)
        self._core_promotions = self._load_list(self._core_promotions_path)

    # ── Persistence ───────────────────────────────────────────────────────────

    def _load_list(self, path: Path) -> List[Dict[str, Any]]:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return data
            except Exception:
                pass
        return []

    def _save_list(self, path: Path, value: List[Dict[str, Any]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_governance_log(self, event: str, details: Dict[str, Any]) -> None:
        self._governance_log.append(
            {"id": str(uuid.uuid4()), "event": event, "at": _now_iso(), "details": details}
        )
        self._governance_log = self._governance_log[-300:]
        self._save_list(self._governance_log_path, self._governance_log)

    # ── Classification & policy ───────────────────────────────────────────────

    def _detect_sensitive_categories(self, content: str) -> List[str]:
        text = (content or "").strip().lower()
        found: List[str] = []
        for category, markers in self._SENSITIVE_MARKERS.items():
            if any(marker.lower() in text for marker in markers):
                found.append(category)
        return found

    def _importance_score(self, content: str) -> float:
        text = (content or "").strip()
        if not text:
            return 0.0
        score = 0.35
        length_bonus = min(len(text) / 240.0, 0.25)
        score += length_bonus
        if any(k in text.lower() for k in ("هدف", "project", "مشروع", "قرار", "priority", "خطة")):
            score += 0.2
        if "!" in text or "مهم" in text:
            score += 0.1
        return round(min(score, 0.95), 2)

    def _needs_approval(self, target_layer: str, sensitive_categories: List[str]) -> bool:
        if target_layer == self.FOUNDER_MEMORY:
            return True
        if target_layer in {self.CORE_IDENTITY, self.CORE_KNOWLEDGE}:
            return True
        return bool(sensitive_categories)

    def _default_target_layer(self, requested_layer: str | None) -> str:
        layer = (requested_layer or self.LEARNED_KNOWLEDGE).strip().lower()
        if layer not in self.LAYERS:
            return self.LEARNED_KNOWLEDGE
        return layer

    # ── Candidate flow ────────────────────────────────────────────────────────

    def submit_candidate(
        self,
        *,
        content: str,
        source: str = "founder",
        requested_layer: str | None = None,
        origin_context: Optional[Dict[str, Any]] = None,
        confidence: float = 0.7,
    ) -> Dict[str, Any]:
        text = (content or "").strip()
        if not text:
            raise ValueError("content is required")

        target_layer = self._default_target_layer(requested_layer)
        sensitive_categories = self._detect_sensitive_categories(text)
        importance = self._importance_score(text)
        needs_approval = self._needs_approval(target_layer, sensitive_categories)

        item: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "memory_type": target_layer,
            "content": text,
            "source": source or "founder",
            "timestamp": _now_iso(),
            "confidence": float(max(0.0, min(confidence, 1.0))),
            "approval_state": "pending" if needs_approval else "not_required",
            "importance_score": importance,
            "sensitive_categories": sensitive_categories,
            "origin_context": origin_context or {},
        }

        self._append_governance_log(
            "memory_candidate_created",
            {
                "item_id": item["id"],
                "target_layer": target_layer,
                "importance_score": importance,
                "needs_approval": needs_approval,
                "sensitive_categories": sensitive_categories,
            },
        )

        if needs_approval:
            approval_id = self._approval_gate.request(
                action="other",
                description=f"Memory write approval for {target_layer}: {text[:100]}",
                requested_by="memory_governance",
                context={"item_id": item["id"], "memory_type": target_layer},
            )
            item["approval_id"] = approval_id
            self._pending_candidates.append(item)
            self._save_list(self._pending_path, self._pending_candidates)
            return {
                "saved": False,
                "status": "pending_approval",
                "approval_id": approval_id,
                "memory_item": dict(item),
            }

        stored = self._store_item(item, target_layer)
        return {
            "saved": True,
            "status": "stored",
            "memory_item": stored,
        }

    def finalize_approval(self, approval_id: str, *, approved_by: str = "naseem") -> Dict[str, Any]:
        approval = self._approval_gate.get(approval_id)
        if not approval:
            raise ValueError("approval not found")

        candidate = next((c for c in self._pending_candidates if c.get("approval_id") == approval_id), None)
        if not candidate:
            return {"stored": False, "status": "no_pending_candidate"}

        status = approval.get("status")
        if status != "approved":
            return {"stored": False, "status": f"approval_{status or 'unknown'}"}

        candidate["approval_state"] = "approved"
        candidate["approved_by"] = approved_by
        candidate["approved_at"] = _now_iso()
        stored = self._store_item(candidate, candidate["memory_type"])
        self._pending_candidates = [c for c in self._pending_candidates if c.get("approval_id") != approval_id]
        self._save_list(self._pending_path, self._pending_candidates)

        self._append_governance_log(
            "memory_candidate_approved_and_stored",
            {
                "approval_id": approval_id,
                "item_id": stored.get("id"),
                "target_layer": stored.get("memory_type"),
            },
        )
        return {"stored": True, "status": "stored", "memory_item": stored}

    def discard_candidate(self, approval_id: str, *, rejected_by: str = "naseem", reason: str = "") -> Dict[str, Any]:
        candidate = next((c for c in self._pending_candidates if c.get("approval_id") == approval_id), None)
        if not candidate:
            return {"discarded": False, "status": "not_found"}

        candidate["approval_state"] = "rejected"
        candidate["rejected_by"] = rejected_by
        candidate["rejection_reason"] = reason
        self._pending_candidates = [c for c in self._pending_candidates if c.get("approval_id") != approval_id]
        self._save_list(self._pending_path, self._pending_candidates)
        self._append_governance_log(
            "memory_candidate_discarded",
            {"approval_id": approval_id, "item_id": candidate.get("id"), "reason": reason},
        )
        return {"discarded": True, "status": "discarded"}

    def _store_item(self, item: Dict[str, Any], target_layer: str) -> Dict[str, Any]:
        layer = self._default_target_layer(target_layer)
        if layer == self.CORE_IDENTITY:
            raise PermissionError("core_identity is read-only")
        if layer == self.CORE_KNOWLEDGE:
            raise PermissionError("core_knowledge is read-only without explicit promotion")
        if layer == self.FOUNDER_MEMORY and item.get("approval_state") != "approved":
            raise PermissionError("founder_memory write requires explicit approval")

        stored = dict(item)
        stored["stored_at"] = _now_iso()
        stored["memory_type"] = layer
        stored.setdefault("source", "founder")
        stored.setdefault("timestamp", _now_iso())
        stored.setdefault("confidence", 0.7)
        stored.setdefault("approval_state", "not_required")

        if layer == self.FOUNDER_MEMORY:
            self._founder_items.append(stored)
            self._founder_items = self._founder_items[-300:]
            self._save_list(self._founder_path, self._founder_items)
        elif layer == self.LEARNED_KNOWLEDGE:
            self._learned_items.append(stored)
            self._learned_items = self._learned_items[-500:]
            self._save_list(self._learned_path, self._learned_items)
        elif layer == self.WORKING_MEMORY:
            self._working_items.append(stored)
            self._working_items = self._working_items[-300:]
            self._save_list(self._working_path, self._working_items)
        else:  # session_memory
            self._session_items.append(stored)
            self._session_items = self._session_items[-100:]
            self._save_list(self._session_path, self._session_items)

        self._append_governance_log(
            "memory_item_stored",
            {"item_id": stored.get("id"), "memory_type": layer, "approval_state": stored.get("approval_state")},
        )
        return stored

    # ── Knowledge governance ───────────────────────────────────────────────────

    def promote_learned_to_core(self, item_id: str, *, reason: str, approved_by: str) -> Dict[str, Any]:
        learned = next((x for x in self._learned_items if x.get("id") == item_id), None)
        if not learned:
            raise ValueError("learned knowledge item not found")
        if not reason.strip():
            raise ValueError("reason is required")

        promoted = {
            "id": str(uuid.uuid4()),
            "from_item_id": item_id,
            "from_layer": self.LEARNED_KNOWLEDGE,
            "to_layer": self.CORE_KNOWLEDGE,
            "content": learned.get("content", ""),
            "source": learned.get("source", "founder"),
            "timestamp": learned.get("timestamp", _now_iso()),
            "confidence": learned.get("confidence", 0.7),
            "approval_state": "approved",
            "approved_by": approved_by,
            "promoted_at": _now_iso(),
            "promotion_reason": reason.strip(),
        }
        self._core_promotions.append(promoted)
        self._core_promotions = self._core_promotions[-200:]
        self._save_list(self._core_promotions_path, self._core_promotions)
        self._append_governance_log(
            "knowledge_promotion",
            {
                "from_layer": self.LEARNED_KNOWLEDGE,
                "to_layer": self.CORE_KNOWLEDGE,
                "from_item_id": item_id,
                "approved_by": approved_by,
            },
        )
        return promoted

    # ── Queries & maintenance ─────────────────────────────────────────────────

    def list_items(self, layer: str) -> List[Dict[str, Any]]:
        layer = self._default_target_layer(layer)
        if layer == self.FOUNDER_MEMORY:
            return [dict(x) for x in self._founder_items]
        if layer == self.LEARNED_KNOWLEDGE:
            return [dict(x) for x in self._learned_items]
        if layer == self.WORKING_MEMORY:
            return [dict(x) for x in self._working_items]
        if layer == self.SESSION_MEMORY:
            return [dict(x) for x in self._session_items]
        if layer == self.CORE_KNOWLEDGE:
            return [dict(x) for x in self._core_promotions]
        return []

    def delete_item(self, layer: str, item_id: str) -> bool:
        layer = self._default_target_layer(layer)
        if layer == self.CORE_IDENTITY:
            return False

        if layer == self.FOUNDER_MEMORY:
            before = len(self._founder_items)
            self._founder_items = [x for x in self._founder_items if x.get("id") != item_id]
            changed = len(self._founder_items) != before
            if changed:
                self._save_list(self._founder_path, self._founder_items)
        elif layer == self.LEARNED_KNOWLEDGE:
            before = len(self._learned_items)
            self._learned_items = [x for x in self._learned_items if x.get("id") != item_id]
            changed = len(self._learned_items) != before
            if changed:
                self._save_list(self._learned_path, self._learned_items)
        elif layer == self.WORKING_MEMORY:
            before = len(self._working_items)
            self._working_items = [x for x in self._working_items if x.get("id") != item_id]
            changed = len(self._working_items) != before
            if changed:
                self._save_list(self._working_path, self._working_items)
        elif layer == self.SESSION_MEMORY:
            before = len(self._session_items)
            self._session_items = [x for x in self._session_items if x.get("id") != item_id]
            changed = len(self._session_items) != before
            if changed:
                self._save_list(self._session_path, self._session_items)
        else:
            before = len(self._core_promotions)
            self._core_promotions = [x for x in self._core_promotions if x.get("id") != item_id]
            changed = len(self._core_promotions) != before
            if changed:
                self._save_list(self._core_promotions_path, self._core_promotions)

        if changed:
            self._append_governance_log("memory_item_deleted", {"item_id": item_id, "memory_type": layer})
        return changed

    def pending_candidates(self) -> List[Dict[str, Any]]:
        return [dict(x) for x in self._pending_candidates]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "layers": {
                self.CORE_IDENTITY: {"read_only": True, "count": 0},
                self.CORE_KNOWLEDGE: {"read_only": True, "count": len(self._core_promotions)},
                self.LEARNED_KNOWLEDGE: {"read_only": False, "count": len(self._learned_items)},
                self.FOUNDER_MEMORY: {"read_only": False, "count": len(self._founder_items)},
                self.WORKING_MEMORY: {"read_only": False, "count": len(self._working_items)},
                self.SESSION_MEMORY: {"read_only": False, "count": len(self._session_items)},
            },
            "pending_candidates": len(self._pending_candidates),
            "governance_log_entries": len(self._governance_log),
            "last_governance_event_at": self._governance_log[-1]["at"] if self._governance_log else None,
        }
