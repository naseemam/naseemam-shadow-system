from pathlib import Path
root = Path(r'C:\Users\DELL\Desktop\Ameer')
output = root / 'missing_arabic_files.txt'
markers = ['## Arabic Support', '## دعم اللغة العربية', 'Arabic dialogue', 'دعم الحوار', 'العربية', 'Arabic']
missing = []
for p in sorted(root.rglob('*.md')):
    if any(part in p.parts for part in ('.git', '.vscode')):
        continue
    text = p.read_text(encoding='utf-8')
    if not any(marker in text for marker in markers):
        missing.append(str(p.relative_to(root)))
with output.open('w', encoding='utf-8') as f:
    for path in missing:
        f.write(path + '\n')
print(f'Wrote {len(missing)} missing files to {output}')
