# Project Ameer

Ameer is a personal AI companion designed to grow with its founder.

## Project Structure

- 01_Docs → Vision, Constitution and planning.
- 02_Research → Research and references.
- 03_Architecture → System design.
- 04_Memory → Long-term memory.
- 05_Journal → Development journal.
- 06_Code → Source code.
- 07_Tests → Testing.
- 08_Backups → Project backups.

The Constitution is the highest authority for this project.

## Local External Test Step

Use this as a fixed development step before and after core changes.

From the project folder:

```powershell
cd C:\Users\DELL\Desktop\Ameer

$env:AMEER_DEBUG="1"

.\.venv\Scripts\python.exe -m uvicorn ameer_server:app --host 127.0.0.1 --port 8016
```

Open the browser:

```text
http://127.0.0.1:8016
```

Quick API test runner:

```powershell
.\scripts\run_local_test.ps1
```

The script will:

- Start the local server in debug mode if it is not already running.
- Wait for `/health`.
- Send identity, project, and greeting test queries.
- Print `intent`, `agent`, `confidence`, `selected_agent`, `reply_generated_by`, and final `reply`.
- Stop the server if the script started it.

## Arabic Support / دعم اللغة العربية
- This project documentation acknowledges Arabic support as a core design requirement.
- يجب أن يتضمن المشروع دعم اللغة العربية في التفاعل والمستندات.
- Arabic dialogue and founder consent principles should be reflected throughout design and implementation.
- All impactful actions and permanent memory changes require the explicit approval of the Founder, Naseem.
- تتطلب أي إجراءات مؤثرة أو تغييرات دائمة في الذاكرة موافقة صريحة من المؤسس نسيم.
