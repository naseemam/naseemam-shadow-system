from pathlib import Path


def _html() -> str:
    return (Path(__file__).resolve().parents[1] / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")


def test_shadow_system_has_the_approved_information_architecture():
    html = _html()
    for required in (
        "نظام الظل",
        "المحادثة الودية",
        "محادثة الأعمال",
        "متابعة العملاء",
        "نسخة إشرافية · متجر حلم الندى",
        "حلم الندى",
        "موقع حلم الندى الأم",
        "برنامج إدارة حلم الندى",
        "حالة مشروع حلم الندى",
        "رابط وإدارة متجر حلم الندى",
        "المدرسة",
        "التداول",
        "موقع التداول",
        "لوحة التداول",
        "بوت التداول",
        "الاستراتيجيات",
        "الصفقات وسجل الأوامر",
        "الأداء والمخاطر",
        "إعدادات التداول",
        "الإدارة الشاملة",
    ):
        assert required in html


def test_chat_rooms_and_approval_controls_are_wired_to_correct_routes():
    html = _html()
    for required in (
        "/friendly-chat",
        "/ask",
        "/chat/approvals/",
        "أوافق وأنفذ",
        "أرفض",
            "postJsonWithRetry",
            "isBusiness?'/ask':'/friendly-chat'",
            "isBusiness?d.chat_approval:null",
    ):
        assert required in html


def test_shadow_ui_uses_live_operational_data_and_separate_local_history():
    html = _html()
    for required in (
        "/ui/runtime",
        "/workers/runtime",
        "/center/dashboard",
        "/center/customers",
        "shadow.business.v1",
        "shadow.friendly.v1",
        "localStorage",
    ):
        assert required in html


def test_business_chat_restores_pending_approvals_and_prevents_duplicate_decisions():
    html = _html()
    for required in (
        'id="loadBusinessApprovals"',
        "استعادة طلبات الموافقة",
        "/chat/approvals/pending",
        "loadPendingApprovals",
        "markApprovalResolved",
        "hasApproval",
        "تمت الموافقة",
        "تم الرفض",
    ):
        assert required in html


def test_dream_main_sites_have_active_preview_and_focus_routes():
    html = _html()
    for required in (
        'data-focus="home"',
        'data-focus="management"',
        'data-focus="status"',
        'data-focus="store"',
        "setDreamFocus",
        "/preview/projects/حلم-الندى",
        "/preview/projects/حلم-الندى-الإدارة",
        "/preview/projects/حلم-الندى-الحالة",
        "/preview/projects/حلم-الندى-المتجر",
    ):
        assert required in html


def test_pending_chat_approval_endpoint_exposes_display_safe_cards_only():
    source = (
        Path(__file__).resolve().parents[1] / "ameer_delivery_bootstrap.py"
    ).read_text(encoding="utf-8")
    for required in (
        '@app.get("/chat/approvals/pending")',
        "Return authenticated, display-safe cards",
        '"approval_id": item.get("approval_id")',
        '"summary": item.get("summary")',
        "_require_agent_access(request)",
    ):
        assert required in source
    assert '"command": item.get("command")' not in source


def test_admin_exposes_delegated_authority_and_delivery_evidence():
    html = _html()
    for required in (
        "صلاحيات تنفيذية شاملة",
        "الحذف النهائي",
        "النشر/التراجع عن النشر",
        "سياسة الصلاحيات #82",
        "تشغيل العمال #83",
        "https://github.com/naseemam/naseemam-shadow-system/pull/82",
        "https://github.com/naseemam/naseemam-shadow-system/pull/83",
        "https://railway.com/project/741a4d8c-47ca-4d34-9efa-084a686d3465/service/f6286e23-63b0-48a3-8c33-28d8696f4968",
        "railwayBuild",
    ):
        assert required in html


def test_business_chat_states_root_asset_gates_without_legacy_delete_or_publish_copy():
    html = _html()

    assert "تظهر بطاقة القرار فقط عند طلب إنشاء موقع أو برنامج أو نظام أو مستودع مستقل جديد." in html
    assert "الحذف والنشر يظهران كبطاقة قرار هنا." not in html
