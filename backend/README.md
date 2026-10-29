# ResearchMind AI — Backend

FastAPI + SQLAlchemy, managed with [uv](https://docs.astral.sh/uv/).

```bash
uv sync                                    # creates .venv and installs deps from uv.lock
cp .env.example .env                       # then fill SUPABASE_URL (and SUPABASE_JWT_SECRET if legacy)
uv run uvicorn app.main:app --reload --port 8000
uv run pytest                              # tests
```

Add a dependency: `uv add <package>` (dev only: `uv add --dev <package>`).
