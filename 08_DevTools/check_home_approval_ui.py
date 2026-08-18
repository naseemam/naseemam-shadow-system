from pathlib import Path
import re

html = Path("09_Assets/web/index.html").read_text(encoding="utf-8")
assert 'id="requestApprovalBtn"' in html
assert 'id="approvalState"' in html
assert 'أوافق وأفتح التنفيذ' in html
assert 'activeApprovalStatus!==\'approved\'' in html
scripts = re.findall(r"<script>(.*?)</script>", html, flags=re.S)
Path("/tmp/ameer_home_inline.js").write_text("\n".join(scripts), encoding="utf-8")
print("home_approval_ui: PASS")
print(f"scripts={len(scripts)}")
