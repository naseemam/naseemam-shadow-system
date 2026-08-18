import os
import signal
import subprocess
import time
from urllib.parse import quote
from urllib.request import urlopen

root = os.path.dirname(os.path.dirname(__file__))
proc = subprocess.Popen(
    ["python3", "start_ameer.py"],
    cwd=root,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    time.sleep(4)
    for path in ["/", "/preview/projects/حلم-الندى", "/preview/projects/حلم-الندى-المتجر", "/preview/projects/حلم-الندى-الإدارة", "/preview/projects/حلم-الندى-الحالة", "/preview/projects/المدرسة", "/preview/projects/التداول", "/center/dashboard", "/gateway/status"]:
        url = "http://127.0.0.1:8000" + quote(path, safe="/")
        try:
            with urlopen(url, timeout=10) as response:
                body = response.read()
                print(f"{path} HTTP:{response.status} bytes:{len(body)}")
        except Exception as exc:
            print(f"{path} ERROR:{exc}")
finally:
    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
