# Knowledge

## Project Memory

## Confirmed Architecture and Runtime Knowledge
- Runtime server: FastAPI-based server documented in `ameer_server.py` and `10_Documentation/Production_Roadmap.md`.
- Startup entrypoint: `start_ameer.py`.
- Current runtime/orchestration includes `AmeerOrchestrator`, `ExecutiveBrain`, and `ResponseFormatter`.
- Inference provider adapters exist for OpenAI and Ollama; the roadmap states no real LLM is fully activated yet.
- Frontend workspace includes chat, projects, memory, system, and home modules, plus stubs for bots, business, development, investment, and websites.
- Governance and architecture documents distinguish Temporary, Project, Founder, and Core memory.

## Confirmed Governance Knowledge
- Founder authority is final.
- Important actions require explicit founder approval.
- Permanent memory entries should include source, confidence level, approval state, and timestamp metadata according to project governance documents.
- Arabic support must preserve the same consent, privacy, and partner-first principles across languages.

## Verified Sources
- `01_Docs/Ameer_Constitution_v0.1.md`
- `03_Architecture/Ameer_Architecture_Overview.md`
- `10_Documentation/Development_Guide_v1.0.md`
- `10_Documentation/Production_Roadmap.md`
- `06_Code/adapters/inference_provider.py`
- `06_Code/executive_brain.py`
