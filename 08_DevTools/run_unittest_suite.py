import os
import subprocess
import sys

repo = r"C:\Users\DELL\Desktop\Ameer"
os.chdir(repo)
modules = [
    '07_Tests.test_executive_orchestrator',
    '07_Tests.test_tool_bus',
    '07_Tests.test_github_connector',
    '07_Tests.test_document_library',
    '07_Tests.test_railway_connector',
]
result = subprocess.run([sys.executable, '-m', 'unittest', *modules], capture_output=True, text=True)
print(result.stdout)
print(result.stderr)
raise SystemExit(result.returncode)
