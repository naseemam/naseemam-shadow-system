from pathlib import Path
p = Path(r'C:\Users\DELL\Desktop\Ameer\meeting.md')
print('exists=', p.exists())
if p.exists():
    print(p.read_text(encoding='utf-8'))
