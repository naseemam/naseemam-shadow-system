# Runtime Architecture

- Startup Launcher: start_ameer.py
- Runtime Application: ameer_server.py
- Server: FastAPI + Uvicorn
- Host: 127.0.0.1
- Port: 8011
- URL: http://127.0.0.1:8011/
- Runtime Status: Frozen (v1.0)
- Compliance: 100%
- Change Policy: Any modification to Entry Point, Server, Host, Port, Runtime, or Folder Structure requires Founder approval.
- Folder Structure:
  - Root Folder:
    09_Assets/web
  - Main Application: ameer_server.py
  - Web Assets: 09_Assets/web/
- Runtime Rules:
  1. No new localhost.
  2. No alternate default port.
  3. No http.server.
  4. Production startup goes through start_ameer.py.
  5. All new pages are routes inside ameer_server.py.
  6. All modules run under the same server.
  7. Future development must preserve this architecture.
