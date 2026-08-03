from pathlib import Path

root = Path(r'C:\Users\DELL\Desktop\Ameer')
section = "\n## Arabic Support / دعم اللغة العربية\n- This document supports Arabic interaction and bilingual system design.\n- يجب أن يدعم هذا المستند الحوار والمفاهيم باللغة العربية.\n- Arabic responses and interfaces should follow founder-approved consent, security, and partner-first behavior.\n- يجب أن تبقى المبادئ نفسها ثابتة في التعامل باللغة العربية.\n"

updated = []
skipped = []

for p in sorted(root.rglob('*.md')):
    if '.git' in p.parts or '.vscode' in p.parts or '.github' in p.parts:
        continue
    text = p.read_text(encoding='utf-8')
    if '## Arabic Support' in text or '## دعم اللغة العربية' in text:
        skipped.append(p.relative_to(root))
        continue
    p.write_text(text.rstrip('\n') + section, encoding='utf-8')
    updated.append(p.relative_to(root))

print(f'Updated {len(updated)} files:')
for p in updated:
    print(p)
print(f'Already containing section: {len(skipped)} files:')
for p in skipped:
    print(p)
