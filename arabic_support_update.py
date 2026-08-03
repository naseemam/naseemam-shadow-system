from pathlib import Path

root = Path(r'C:\Users\DELL\Desktop\Ameer')
section = "\n## Arabic Support / دعم اللغة العربية\n- This document supports Arabic interaction and bilingual system design.\n- يجب أن يدعم هذا المستند الحوار والمفاهيم باللغة العربية.\n- Arabic responses and interfaces should follow founder-approved consent, security, and partner-first behavior.\n- يجب أن تبقى المبادئ نفسها ثابتة في التعامل باللغة العربية.\n"
markers = ['## Arabic Support', '## دعم اللغة العربية', 'Arabic dialogue', 'دعم الحوار', 'العربية']
updated = []
skipped = []
errors = []
for p in sorted(root.rglob('*.md')):
    if any(part in p.parts for part in ('.git', '.vscode', '.github')):
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception as e:
        errors.append((p, str(e)))
        continue
    if any(marker in text for marker in markers):
        skipped.append(p.relative_to(root))
        continue
    p.write_text(text.rstrip('\n') + section, encoding='utf-8')
    updated.append(p.relative_to(root))

with open(root / 'arabic_support_update.log', 'w', encoding='utf-8') as f:
    f.write(f'Updated {len(updated)} files:\n')
    for p in updated:
        f.write(str(p) + '\n')
    f.write(f'\nSkipped {len(skipped)} files already containing Arabic markers:\n')
    for p in skipped:
        f.write(str(p) + '\n')
    if errors:
        f.write(f'\nErrors {len(errors)}:\n')
        for p, e in errors:
            f.write(f'{p}: {e}\n')
print('done')
