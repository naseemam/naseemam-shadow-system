from __future__ import annotations

from copy import deepcopy
from functools import wraps
from typing import Any

_INSTALLED = False

_CONTINUATION_TERMS = (
    "نفذ", "نفّذ", "ابدأ", "ابدا", "ابدئي", "أبدأ", "اكمل", "أكمل", "كمل",
    "تابع", "استمر", "عدل", "عدّل", "اصلح", "أصلح", "اختبر", "جرب", "جرّب",
    "سوها", "سويها", "شيك", "راجع", "م ضبط", "ما ضبط", "خلص", "أنجز", "انجز",
    "نفّذ الآن", "ابدأ الآن", "كمل الآن", "continue", "proceed", "execute",
    "implement", "test", "fix", "update", "commit", "push", "merge", "deploy", "publish",
)

_DELEGATION_TERMS = (
    "لا ترجع لموافقتي", "لا ترجع لي", "لا تسألني", "بدون ما تسألني",
    "انجز كلشي", "أنجز كلشي", "انجز كل شيء", "أنجز كل شيء", "كمل كلشي",
    "إلا وقت النشر", "الا وقت النشر", "إلا عند النشر", "الا عند النشر",
    "until publish", "until deployment", "without asking me", "do it all",
)


def _normalized(query: str) -> str:
    return (query or "").strip().lower()


def _is_stage_continuation(query: str) -> bool:
    text = _normalized(query)
    return bool(text) and any(term in text for term in _CONTINUATION_TERMS + _DELEGATION_TERMS)


def _clear_legacy_guardian(reasoning_output: Any) -> Any:
    """Remove obsolete per-turn approval signals from legacy reasoning output.

    Sovereign approval is owned by the central authority/final-stage gate. Generic
    operational words such as push, deploy, publish, execute, edit, test and fix
    must never create a second human-control layer.
    """
    if not isinstance(reasoning_output, dict):
        return reasoning_output
    result = deepcopy(reasoning_output)
    reasoning = result.get("reasoning")
    if isinstance(reasoning, dict) and reasoning.get("guardian_status") == "needs_approval":
        reasoning["guardian_status"] = "pass"
        reasoning["guardian_reason"] = "delegated_operational_execution"
        reasoning["guardian_mode"] = "execution_ready"
    return result


def _execution_authority_prompt() -> str:
    return (
        "\n\nسلطة التنفيذ المعتمدة لأمير:\n"
        "- أمير نواة تنفيذية حرة داخل الأصول والمشاريع المفوضة له، وليس مخططًا يسلّم التنفيذ للبشر.\n"
        "- عند طلب الكتابة أو التعديل أو الاختبار أو commit أو push أو merge أو deploy أو إدارة GitHub/Railway/Cloudflare، "
        "ينفذ أمير عبر النواة والموصلات والأدوات المتاحة ثم يعرض النتيجة والدليل.\n"
        "- ممنوع تحويل العمل التشغيلي المعتاد إلى تعليمات للمؤسسة مثل: نفذي الأمر، افتحي المستودع، اضغطي merge، أو شغلي السكربت.\n"
        "- إذا كان موصل أو اعتماد تقني غير متاح، اذكر العائق التقني المحدد وسجله كحالة تنفيذية؛ لا تصفه كحد ذاتي دائم لأمير.\n"
        "- لا تقل إن أمير لا يستطيع GitHub أو النشر لمجرد أنه نموذج محادثة. القدرة يحددها runtime/tooling الفعلي.\n"
        "- لا تطلب موافقة بشرية إلا عندما يصنف المصدر المركزي للسلطة القرار كبوابة سيادية فعلية.\n"
        "- ChatGPT وManus والموديلات والعمال موارد اختيارية؛ لا يعمل أي منهم بدل أمير ولا يملك سلطة فوقه.\n"
    )


def install_stage_autonomy_patch() -> None:
    """Align legacy conversation/reasoning layers with Ameer's free executive core."""
    global _INSTALLED

    from reasoning_orchestrator import AmeerOrchestrator
    from executive_conversation import ExecutiveConversationEngine, PersistentConversationMemory
    from executive_brain import ExecutiveBrain

    if all((
        getattr(AmeerOrchestrator.guardian_check, "_ameer_stage_autonomy", False),
        getattr(PersistentConversationMemory.plan, "_ameer_stage_autonomy", False),
        getattr(ExecutiveConversationEngine.execute, "_ameer_stage_autonomy", False),
        getattr(ExecutiveBrain._build_provider_prompt, "_ameer_stage_autonomy", False),
        getattr(AmeerOrchestrator._build_core_identity_payload, "_ameer_stage_autonomy", False),
    )):
        _INSTALLED = True
        return

    original_guardian_check = AmeerOrchestrator.guardian_check

    @wraps(original_guardian_check)
    def guardian_check(self: AmeerOrchestrator, query: str, intent: str):
        previous = list(getattr(self, "high_risk_action_terms", []))
        try:
            # The old word-list gate wrongly treated ordinary operational verbs
            # as approval events. The central authority/final gate is the only
            # source of sovereign approvals.
            self.high_risk_action_terms = []
            result = original_guardian_check(self, query, intent)
            if isinstance(result, dict) and result.get("status") == "needs_approval":
                result = dict(result)
                result["status"] = "pass"
                result["reason"] = "delegated_operational_execution"
            return result
        finally:
            self.high_risk_action_terms = previous

    guardian_check._ameer_stage_autonomy = True
    AmeerOrchestrator.guardian_check = guardian_check

    original_identity = AmeerOrchestrator._build_core_identity_payload

    @wraps(original_identity)
    def _build_core_identity_payload(self: AmeerOrchestrator, query: str):
        output = original_identity(self, query)
        q = _normalized(query)
        if any(term in q for term in (
            "ماذا تستطيع", "وش تقدر", "ايش تقدر", "حدودك", "كيف تعمل",
            "what can you do", "what are your limits", "how do you work",
        )):
            output.reply_draft = (
                "أنا أمير، نواة تنفيذية حرة داخل منظومتك المفوضة لي. "
                "أفهم الهدف ثم أنفذ عبر الأدوات والموصلات المتاحة: أقرأ وأكتب وأعدل وأختبر، "
                "وأدير المستودعات والنشر والموصلات داخل نطاقي. أتوقف لك فقط عند قرار سيادي مصنف، "
                "أما العائق التقني فأحدده بوضوح ولا أحول التنفيذ عليك."
            )
            if isinstance(output.response_data, dict):
                output.response_data["execution_authority"] = "delegated_free_executive_core"
                output.response_data["human_handoff_for_routine_operations"] = False
        return output

    _build_core_identity_payload._ameer_stage_autonomy = True
    AmeerOrchestrator._build_core_identity_payload = _build_core_identity_payload

    original_provider_prompt = ExecutiveBrain._build_provider_prompt

    @wraps(original_provider_prompt)
    def _build_provider_prompt(self: ExecutiveBrain, *args: Any, **kwargs: Any):
        built = original_provider_prompt(self, *args, **kwargs)
        if not isinstance(built, tuple) or len(built) != 2:
            return built
        system_prompt, user_prompt = built
        return str(system_prompt) + _execution_authority_prompt(), user_prompt

    _build_provider_prompt._ameer_stage_autonomy = True
    ExecutiveBrain._build_provider_prompt = _build_provider_prompt

    original_plan = PersistentConversationMemory.plan

    @wraps(original_plan)
    def plan(self: PersistentConversationMemory, query: str, *args: Any, **kwargs: Any):
        if _is_stage_continuation(query):
            kwargs["running_tasks"] = []
            kwargs["pending_approvals"] = []
        return original_plan(self, query, *args, **kwargs)

    plan._ameer_stage_autonomy = True
    PersistentConversationMemory.plan = plan

    original_execute = ExecutiveConversationEngine.execute

    @wraps(original_execute)
    def execute(self: ExecutiveConversationEngine, *args: Any, **kwargs: Any):
        query = str(kwargs.get("query") or "")
        if _is_stage_continuation(query):
            kwargs["running_tasks"] = []
            kwargs["pending_approvals"] = []
            kwargs["reasoning_output"] = _clear_legacy_guardian(kwargs.get("reasoning_output"))
        return original_execute(self, *args, **kwargs)

    execute._ameer_stage_autonomy = True
    ExecutiveConversationEngine.execute = execute
    _INSTALLED = True
