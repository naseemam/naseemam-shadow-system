from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "06_Code"))

from kernel.chat_media import ChatMediaStore


def test_chat_media_store_extracts_price_sheet_context(tmp_path: Path):
    store = ChatMediaStore(tmp_path)
    attachment = store.save(
        filename="اسعار-الاصناف.csv",
        content_type="text/csv",
        data="الصنف,السعر,المخزون\nعطر,120,8\n".encode("utf-8"),
    )

    context, public = store.attachment_context([attachment["attachment_id"]])

    assert public[0]["filename"] == "اسعار-الاصناف.csv"
    assert public[0]["category"] == "spreadsheet"
    assert "عطر,120,8" in context
    assert store.payload_path(attachment["attachment_id"]).is_file()


def test_chat_media_store_rejects_unapproved_file_types(tmp_path: Path):
    store = ChatMediaStore(tmp_path)

    try:
        store.save(filename="unsafe.exe", content_type="application/octet-stream", data=b"x")
    except ValueError as exc:
        assert str(exc) == "unsupported_attachment_type"
    else:
        raise AssertionError("unsupported file type was accepted")


def test_upload_endpoint_persists_business_attachment(tmp_path: Path):
    import ameer_server

    original_store = ameer_server.CHAT_MEDIA
    ameer_server.CHAT_MEDIA = ChatMediaStore(tmp_path)
    try:
        client = TestClient(ameer_server.app)
        response = client.post(
            "/chat/uploads",
            data={"room": "business"},
            files={"file": ("identity.txt", b"brand colors: blue and gold", "text/plain")},
        )
        assert response.status_code == 200
        attachment = response.json()["attachment"]
        assert attachment["filename"] == "identity.txt"
        assert attachment["download_url"].startswith("/chat/uploads/")

        download = client.get(attachment["download_url"])
        assert download.status_code == 200
        assert download.content == b"brand colors: blue and gold"
    finally:
        ameer_server.CHAT_MEDIA = original_store


def test_business_ui_exposes_upload_voice_and_connection_retry_controls():
    html = (ROOT / "09_Assets" / "web" / "index.html").read_text(encoding="utf-8")

    for required in (
        'id="businessAttach"',
        'id="businessFiles"',
        'id="businessVoice"',
        "uploadBusinessFiles",
        "toggleBusinessVoice",
        "postJsonWithRetry",
        "/chat/uploads",
        "تعذر الاتصال بالخادم بعد إعادة المحاولة",
    ):
        assert required in html
