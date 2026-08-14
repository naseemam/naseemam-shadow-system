from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from kernel.business_operations import BusinessOperations
from kernel.delivery_execution import DeliveryExecutiveKernel
from kernel.google_workspace import GoogleWorkspaceClient, GoogleWorkspaceConfigurationError
from kernel.repository_execution import RepositoryTaskDecomposer


class AgentOperations:
    """Multi-domain operational tool hub for Ameer as an agent."""

    EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)

    def __init__(self, workspace_root: str | Path) -> None:
        self.business = BusinessOperations(workspace_root)
        self.google = GoogleWorkspaceClient()

    def capabilities(self) -> Dict[str, Any]:
        return {
            "agent_mode": True,
            "domains": {
                "software_builder": ["repository_write", "test", "git_push", "pull_request", "merge", "railway_deploy"],
                "communications": ["gmail_search", "gmail_read", "gmail_send"],
                "calendar": ["calendar_list", "calendar_create", "calendar_update", "calendar_delete"],
                "business": [
                    "products", "inventory", "low_stock", "employees", "customers", "bookings", "orders", "dashboard"
                ],
            },
            "google_configured": self.google.configured,
            "business_store": str(self.business.db_path),
        }

    def detect(self, command: str) -> Optional[str]:
        text = (command or "").strip().lower()
        if not text:
            return None
        if any(x in text for x in ("ارسل بريد", "أرسل بريد", "ارسل ايميل", "أرسل إيميل", "send email", "send mail")):
            return "email.send"
        if any(x in text for x in ("ابحث في البريد", "فتش البريد", "search email", "search mail", "inbox")):
            return "email.search"
        if any(x in text for x in ("مواعيدي", "اعرض التقويم", "اعرض المواعيد", "calendar events", "list events")):
            return "calendar.list"
        if any(x in text for x in ("أنشئ موعد", "انشئ موعد", "اضف موعد", "أضف موعد", "create event", "add event")):
            return "calendar.create"
        if any(x in text for x in ("المخزون المنخفض", "نواقص المخزون", "low stock")):
            return "inventory.low_stock"
        if any(x in text for x in ("اعرض المنتجات", "قائمة المنتجات", "list products")):
            return "products.list"
        if any(x in text for x in ("اضف منتج", "أضف منتج", "add product")):
            return "products.add"
        if any(x in text for x in ("الموظفين", "قائمة الموظفين", "list employees")):
            return "employees.list"
        if any(x in text for x in ("اضف موظف", "أضف موظف", "add employee")):
            return "employees.add"
        if any(x in text for x in ("الحجوزات", "قائمة الحجوزات", "list bookings")):
            return "bookings.list"
        if any(x in text for x in ("لوحة المركز", "ملخص المركز", "لوحة المتجر", "business dashboard")):
            return "business.dashboard"
        return None

    @staticmethod
    def _number_after(text: str, labels: tuple[str, ...], default: float = 0) -> float:
        for label in labels:
            m = re.search(rf"{re.escape(label)}\s*[:=]?\s*(-?\d+(?:\.\d+)?)", text, flags=re.IGNORECASE)
            if m:
                return float(m.group(1))
        return default

    def execute_natural(self, action: str, command: str) -> Dict[str, Any]:
        text = command.strip()
        if action == "email.send":
            emails = self.EMAIL_RE.findall(text)
            if not emails:
                return {"status": "needs_parameters", "missing": ["to"], "message": "أحتاج عنوان البريد المستلم."}
            subject_match = re.search(r"(?:عنوان|subject)\s*[:=]?\s*([^\n]+?)(?=\s+(?:نص|رسالة|body|message)\s*[:=]?|$)", text, re.IGNORECASE)
            body_match = re.search(r"(?:نص|رسالة|body|message)\s*[:=]?\s*(.+)$", text, re.IGNORECASE | re.DOTALL)
            subject = subject_match.group(1).strip() if subject_match else "رسالة من أمير"
            body = body_match.group(1).strip() if body_match else ""
            if not body:
                return {"status": "needs_parameters", "missing": ["body"], "message": "أحتاج نص الرسالة قبل الإرسال."}
            return {"status": "completed", "action": action, "result": self.google.send_email(emails[0], subject, body)}

        if action == "email.search":
            q = re.sub(r"^(?:ابحث في البريد عن|فتش البريد عن|search (?:email|mail)(?: for)?)\s*", "", text, flags=re.IGNORECASE)
            return {"status": "completed", "action": action, "result": self.google.search_messages(q, max_results=20)}

        if action == "calendar.list":
            return {
                "status": "needs_parameters",
                "action": action,
                "missing": ["time_min"],
                "message": "يلزم نطاق زمني واضح للمواعيد، أو استخدم /agent/action بقيمة time_min.",
            }

        if action == "calendar.create":
            return {
                "status": "needs_parameters",
                "action": action,
                "missing": ["summary", "start", "end"],
                "message": "أحتاج اسم الموعد ووقت البداية والنهاية.",
            }

        if action == "inventory.low_stock":
            return {"status": "completed", "action": action, "result": self.business.low_stock()}
        if action == "products.list":
            return {"status": "completed", "action": action, "result": self.business.list_products()}
        if action == "employees.list":
            return {"status": "completed", "action": action, "result": self.business.list_employees()}
        if action == "bookings.list":
            return {"status": "completed", "action": action, "result": self.business.list_bookings()}
        if action == "business.dashboard":
            return {"status": "completed", "action": action, "result": self.business.dashboard()}
        if action == "products.add":
            name = re.sub(r"^.*?(?:اضف منتج|أضف منتج|add product)\s*", "", text, flags=re.IGNORECASE)
            name = re.split(r"\s+(?:كمية|stock|سعر|price|حد الطلب|reorder)\b", name, maxsplit=1, flags=re.IGNORECASE)[0].strip(" :،,")
            if not name:
                return {"status": "needs_parameters", "missing": ["name"]}
            stock = self._number_after(text, ("كمية", "stock"), 0)
            price = self._number_after(text, ("سعر", "price"), 0)
            reorder = self._number_after(text, ("حد الطلب", "reorder"), 0)
            return {"status": "completed", "action": action, "result": self.business.add_product(name, stock=stock, price=price, reorder_level=reorder)}
        if action == "employees.add":
            name = re.sub(r"^.*?(?:اضف موظف|أضف موظف|add employee)\s*", "", text, flags=re.IGNORECASE).strip(" :،,")
            if not name:
                return {"status": "needs_parameters", "missing": ["name"]}
            return {"status": "completed", "action": action, "result": self.business.add_employee(name)}
        return {"status": "ignored", "action": action}

    def execute_structured(self, action: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        p = payload or {}
        try:
            if action == "email.send":
                result = self.google.send_email(p["to"], p.get("subject", "رسالة من أمير"), p["body"], cc=p.get("cc", ""), bcc=p.get("bcc", ""))
            elif action == "email.search":
                result = self.google.search_messages(p.get("query", ""), max_results=int(p.get("max_results", 20)))
            elif action == "email.get":
                result = self.google.get_message(p["message_id"], format=p.get("format", "metadata"))
            elif action == "calendar.list":
                result = self.google.list_events(time_min=p["time_min"], time_max=p.get("time_max", ""), max_results=int(p.get("max_results", 50)))
            elif action == "calendar.create":
                result = self.google.create_event(p["summary"], p["start"], p["end"], timezone=p.get("timezone", "Asia/Riyadh"), description=p.get("description", ""), attendees=p.get("attendees"), location=p.get("location", ""))
            elif action == "calendar.update":
                result = self.google.update_event(p["event_id"], p.get("changes") or {})
            elif action == "calendar.delete":
                result = self.google.delete_event(p["event_id"])
            elif action == "products.add":
                result = self.business.add_product(p["name"], sku=p.get("sku", ""), price=float(p.get("price", 0)), stock=float(p.get("stock", 0)), reorder_level=float(p.get("reorder_level", 0)))
            elif action == "products.list":
                result = self.business.list_products(active_only=bool(p.get("active_only", True)))
            elif action == "inventory.adjust":
                result = self.business.adjust_stock(int(p["product_id"]), float(p["delta"]), reason=p.get("reason", "agent"))
            elif action == "inventory.low_stock":
                result = self.business.low_stock()
            elif action == "employees.add":
                result = self.business.add_employee(p["name"], role=p.get("role", ""), phone=p.get("phone", ""), email=p.get("email", ""))
            elif action == "employees.list":
                result = self.business.list_employees(status=p.get("status", "active"))
            elif action == "customers.add":
                result = self.business.add_customer(p["name"], phone=p.get("phone", ""), email=p.get("email", ""), notes=p.get("notes", ""))
            elif action == "bookings.create":
                result = self.business.create_booking(p["title"], p["starts_at"], ends_at=p.get("ends_at", ""), customer_id=p.get("customer_id"), employee_id=p.get("employee_id"), notes=p.get("notes", ""))
            elif action == "bookings.list":
                result = self.business.list_bookings(status=p.get("status"), limit=int(p.get("limit", 100)))
            elif action == "orders.create":
                result = self.business.create_order(customer_id=p.get("customer_id"), total=float(p.get("total", 0)), notes=p.get("notes", ""))
            elif action == "business.dashboard":
                result = self.business.dashboard()
            else:
                return {"status": "ignored", "action": action, "reason": "unknown_agent_action"}
            return {"status": "completed", "action": action, "result": result}
        except GoogleWorkspaceConfigurationError as exc:
            return {"status": "blocked", "action": action, "reason": "google_not_configured", "detail": str(exc)}
        except (KeyError, ValueError, OSError) as exc:
            return {"status": "blocked", "action": action, "reason": type(exc).__name__, "detail": str(exc)}


class AgentTaskDecomposer:
    """Routes agent and delivery commands into the execution lane before normal decomposition."""

    DELIVERY_MARKERS = ("push", "ادفع", "إدفع", "merge", "ادمج", "دمج", "deploy", "انشر", "أنشر", "railway", "ريلوي", "rollback", "تراجع عن النشر")

    def __init__(self, workspace_root: str, agent_ops: AgentOperations) -> None:
        self._base = RepositoryTaskDecomposer(workspace_root)
        self._agent = agent_ops

    def decompose(self, command: str) -> Dict[str, Any]:
        if self._agent.detect(command):
            return {"intent": "agent_action", "command": command, "tasks": [], "task_count": 0}
        text = (command or "").lower()
        if any(marker.lower() in text for marker in self.DELIVERY_MARKERS):
            return {"intent": "delivery_action", "command": command, "tasks": [], "task_count": 0}
        return self._base.decompose(command)


class AgentExecutiveKernel(DeliveryExecutiveKernel):
    """Ameer agent kernel: business + communications + calendar + software delivery."""

    def __init__(self, workspace_root: str | Path) -> None:
        super().__init__(workspace_root)
        self.agent_ops = AgentOperations(workspace_root)
        self.task_decomposer = AgentTaskDecomposer(str(Path(workspace_root).resolve()), self.agent_ops)

    @staticmethod
    def _trace(intent: str, result: Dict[str, Any]) -> Dict[str, Any]:
        status = str(result.get("status") or "blocked")
        accepted = status in {"completed", "needs_parameters"}
        if status == "completed":
            message = f"تم تنفيذ {result.get('action', intent)} بنجاح."
        elif status == "needs_parameters":
            message = str(result.get("message") or "أحتاج معلومات إضافية لإكمال التنفيذ.")
        else:
            message = str(result.get("detail") or result.get("reason") or "تعذر التنفيذ.")
        return {
            "pipeline": [{"stage": intent, "status": status}],
            "final": {
                "accepted": accepted,
                "completed": 1 if status == "completed" else 0,
                "results": [{"status": status, "content": message, "data": result}],
                "message": message,
            },
        }

    def execute_command(self, command: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
        agent_action = self.agent_ops.detect(command)
        if agent_action:
            return self._trace("agent_action", self.agent_ops.execute_natural(agent_action, command))
        delivery_action = self.delivery.detect(command)
        if delivery_action:
            return self._trace("delivery_action", self.delivery.execute(delivery_action, command))
        return super().execute_command(command, *args, **kwargs)
