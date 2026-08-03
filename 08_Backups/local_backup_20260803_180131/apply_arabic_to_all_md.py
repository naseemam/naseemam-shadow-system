from pathlib import Path

root = Path(r'C:\Users\DELL\Desktop\Ameer')
section = "\n## Arabic Support / دعم اللغة العربية\n- This document supports Arabic interaction and bilingual system design.\n- يجب أن يدعم هذا المستند الحوار والمفاهيم باللغة العربية.\n- Arabic responses and interfaces should follow founder-approved consent, security, and partner-first behavior.\n- يجب أن تبقى المبادئ نفسها ثابتة في التعامل باللغة العربية.\n"
marker = '## Arabic Support / دعم اللغة العربية'
updated = []
skipped = []
errors = []

for p in sorted(root.rglob('*.md')):
    if any(part in p.parts for part in ('.git', '.vscode')):
        continue
    if p.is_dir():
        continue
    try:
        text = p.read_text(encoding='utf-8')
    except Exception as exc:
        errors.append((p.relative_to(root), str(exc)))
        continue
    if marker in text:
        skipped.append(p.relative_to(root))
        continue
    new_text = text.rstrip('\n') + section
    try:
        p.write_text(new_text, encoding='utf-8')
        updated.append(p.relative_to(root))
    except Exception as exc:
        errors.append((p.relative_to(root), str(exc)))

log_path = root / 'arabic_support_update.log'
with log_path.open('w', encoding='utf-8') as log_file:
    log_file.write(f'Updated {len(updated)} files:\n')
    for path in updated:
        log_file.write(f'{path}\n')
    log_file.write(f'\nSkipped {len(skipped)} files already containing the standard Arabic support heading:\n')
    for path in skipped:
        log_file.write(f'{path}\n')
    if errors:
        log_file.write(f'\nErrors {len(errors)}:\n')
        for path, error in errors:
            log_file.write(f'{path}: {error}\n')
print('done')
