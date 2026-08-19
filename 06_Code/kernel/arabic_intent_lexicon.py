"""Unified Arabic intent lexicon for Ameer.

The lexicon is deliberately conservative: friendly language is conversational unless an
explicit action verb is present. It classifies a request into a safe route before any
executor is selected; it does not itself execute tools or grant permissions.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class IntentMatch:
    intent: str
    route: str
    explicit_action: bool
    friendly: bool
    requires_approval: bool
    confidence: float
    matched_terms: Tuple[str, ...]
    canonical_command: str
    needs_context: bool = False
    execution_candidate: bool = False


# Phrase-first ordering prevents a single token from stealing a more specific phrase.
LEXICON: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "conversation": {
        "greeting": ("مرحبا", "مرحباً", "اهلا", "أهلا", "السلام عليكم", "صباح الخير", "مساء الخير"),
        "courtesy": ("شكرا", "شكرًا", "ممتاز", "رائع", "تمام", "حسنا", "حسنًا", "يعطيك العافية", "كيف حالك", "كيفك"),
        "status_question": ("ما الأخبار", "وش الأخبار", "كيف وضعك", "كيف حال العمل", "ما الذي يحدث"),
        "farewell": ("مع السلامة", "تصبح على خير", "إلى اللقاء"),
    },
    "read": {
        "read": ("اقرأ", "اقرئي", "قراءة", "اعرض", "أعرض", "أظهر", "استعرض", "افتح", "شاهد", "اطلع على", "تحقق من الحالة"),
        "review": ("راجع المستودع", "راجع الكود", "حلل المستودع", "افحص", "دقق", "تدقيق"),
        "extract": ("استخرج", "استخراج", "حدد من الملف", "استخلص"),
    },
    "plan": {
        "plan": ("خطط", "خطّط", "خطة", "خطه", "رتب", "رتّب", "اقترح خطة", "ضع خطة", "حدد الخطوات", "تحديد الخطوات"),
        "design": ("صمم خطة", "صمّم خطة", "تصميم خطة", "صمم المعمارية", "صمّم المعمارية", "تصميم النظام"),
    },
    "write": {
        "create": ("اكتب", "كتابة", "أنشئ", "انشئ", "إنشاء", "اصنع", "ابن", "ابنِ", "بناء"),
        "edit": ("عدل", "عدّل", "تعديل", "حرر", "حرّر", "تحرير", "غيّر", "غير"),
        "improve": ("تحسين واجهة المستخدم", "تحسين الواجهة", "تحسين واجهة", "تحسن واجهة المستخدم", "تحسن الواجهة", "تحسّن الواجهة", "حسّن الواجهة", "حسن الواجهة", "طوّر الواجهة", "طور الواجهة", "تطوير الواجهة", "improve ui", "enhance frontend"),
        "design_ui": ("صمم واجهة", "صمّم واجهة", "تصميم واجهة", "صمم صفحة", "صمّم صفحة", "تصميم الصفحة"),
        "execute": ("نفذ", "نفّذ", "تنفيذ", "شغل", "شغّل", "تشغيل", "سوي", "سوه", "سوها"),
    },
    "test": {
        "test": ("اختبر", "اختبره", "اختبار", "اختبارات", "شغل الاختبارات", "شغّل الاختبارات", "نفذ الاختبار", "نفّذ الاختبار", "تحقق بالاختبار"),
    },
    "publish": {
        "publish": ("انشر", "أنشر", "نشر", "انشر على", "ادفع", "إدفع", "رفع إلى", "ارفع إلى", "ادمج", "إدمج", "دمج", "ترقية الإنتاج"),
    },
    "approval": {
        "approve": ("وافق", "موافق", "أوافق", "اعتمد", "اعتماد", "أجيز", "إجازة"),
        "reject": ("ارفض", "أرفض", "رفض", "لا توافق"),
    },
}

_FRIENDLY_FILLERS = ("لو سمحت", "من فضلك", "ممكن", "هل تستطيع", "يا أمير", "أمير")
_ACTION_INTENTS = {"read", "plan", "write", "test", "publish", "approval"}
# النشر فعل تنفيذي مفوض داخل أصل قائم. intent "approval" هنا يعني
# التعامل مع قرار موافقة موجود، لا فتح موافقة جديدة لمجرد وجود أثر خارجي.
_APPROVAL_INTENTS = {"approval"}
_EXECUTION_TARGETS = ("ملف", "كود", "واجهة", "صفحة", "مستودع", "مشروع", "موقع", "تطبيق", "زر", "css", "html", "script", "repository", "project", "website", "frontend", "ui")


def normalize_arabic(text: str) -> str:
    value = (text or "").strip().lower()
    value = re.sub(r"[ًٌٍَُِّْـ]", "", value)
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    value = value.replace("ى", "ي").replace("ؤ", "و").replace("ئ", "ي")
    value = re.sub(r"\s+", " ", value)
    return value


def _find_matches(normalized: str) -> Tuple[str, ...]:
    found = []
    for route, groups in LEXICON.items():
        for terms in groups.values():
            for term in terms:
                if normalize_arabic(term) in normalized:
                    found.append(term)
    # Longest first, stable and de-duplicated.
    return tuple(dict.fromkeys(sorted(found, key=len, reverse=True)))


def classify_arabic_intent(text: str) -> IntentMatch:
    raw = (text or "").strip()
    normalized = normalize_arabic(raw)
    matches = _find_matches(normalized)
    friendly = any(normalize_arabic(x) in normalized for x in _FRIENDLY_FILLERS)

    # Explicit operational phrases win over courtesy fillers. Pure social turns never execute.
    route_scores = {route: 0 for route in LEXICON}
    for route, groups in LEXICON.items():
        for terms in groups.values():
            route_scores[route] += sum(1 for term in terms if normalize_arabic(term) in normalized)

    if not any(route_scores[r] for r in _ACTION_INTENTS):
        return IntentMatch("conversation", "conversation", False, True, False, 0.98, matches, raw)

    # Test/publish/approval are more specific than generic execution verbs.
    # Publishing is classified for delivery routing but not treated as a founder
    # approval gate; root-asset creation is decided later by ameer_authority.
    priority = ("approval", "publish", "test", "read", "plan", "write")
    intent = max(priority, key=lambda route: route_scores[route])
    explicit = True
    needs_context = intent in {"write", "publish", "test"} and len(normalized.split()) <= 2
    confidence = min(0.99, 0.70 + 0.08 * route_scores[intent])
    execution_candidate = intent in {"read", "test", "publish", "approval"} or any(token in normalized for token in _EXECUTION_TARGETS)
    return IntentMatch(
        intent=intent,
        route=intent,
        explicit_action=explicit,
        friendly=friendly,
        requires_approval=intent in _APPROVAL_INTENTS,
        confidence=confidence,
        matched_terms=matches,
        canonical_command=raw,
        needs_context=needs_context,
        execution_candidate=execution_candidate,
    )
