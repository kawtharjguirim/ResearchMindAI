# ResearchMind AI

Multimodal scientific intelligence SaaS platform — Integrated Development Project, 5DS2, ESPRIM (team DeepMinds).

```
researchmind-ai/
├── frontend/          Next.js 15 + TypeScript + Tailwind CSS v4 + Supabase Auth
├── backend/           FastAPI + SQLAlchemy + PostgreSQL (SQLite for quick local dev)
└── docker-compose.yml PostgreSQL + backend
```

## How authentication works

1. The **frontend** signs users in with Supabase Auth (email/password, Google, GitHub, LinkedIn).
2. Every API call sends the Supabase access token: `Authorization: Bearer <token>`.
3. The **backend** never sees passwords. It verifies the token signature (HS256 secret or JWKS),
   reads the user id from the `sub` claim, and filters every query on it (data isolation).

## 1. Supabase setup (once)

1. Create a project on [supabase.com](https://supabase.com).
2. **Authentication → Providers**: Email is on by default. Enable Google / GitHub / LinkedIn (OIDC) if you want the social buttons to work.
3. **Authentication → URL Configuration**:
   - Site URL: `http://localhost:3000`
   - Redirect URLs: add `http://localhost:3000/auth/callback`
4. **Project Settings → API**: copy the project URL and the `anon` public key.
5. **Project Settings → JWT Keys**: if your project still uses the legacy JWT secret, copy it for the backend.
   Projects using the new asymmetric signing keys need no secret: the backend fetches the public keys (JWKS).

## 2. Backend (uv)

Install uv once: `pip install uv` (or see https://docs.astral.sh/uv/getting-started/installation/).

```bash
cd backend
uv sync                       # creates .venv with Python 3.12 and installs deps from uv.lock
cp .env.example .env          # then fill SUPABASE_URL (and SUPABASE_JWT_SECRET if legacy)
uv run uvicorn app.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Tests: `uv run pytest`
- Add a dependency: `uv add <package>` — dev only: `uv add --dev <package>`

With PostgreSQL in Docker instead of SQLite: `docker compose up --build` from the repository root.

## 3. Frontend

```bash
cd frontend
npm install
cp .env.example .env.local    # then fill the Supabase URL, anon key and API URL
npm run dev
```

Open http://localhost:3000 → you are sent to **Sign in** → create an account → **My projects**.

## API (v1)

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | public | Health check |
| GET | `/api/v1/me` | token | Current user from the token |
| GET | `/api/v1/projects` | token | List the user's projects |
| GET | `/api/v1/projects/stats` | token | Dashboard counters |
| POST | `/api/v1/projects` | token | Create a project |
| GET | `/api/v1/projects/{id}` | token | Get one project |
| PATCH | `/api/v1/projects/{id}` | token | Update a project |
| DELETE | `/api/v1/projects/{id}` | token | Delete a project |

## Status

| Module | Frontend | Backend |
| --- | --- | --- |
| Sign in / Sign up (email + OAuth) | Done | Token verification done |
| My projects (list, stats, create) | Done | Done |
| Sources (upload, URL, status) | Placeholder | To do |
| Research assistant (RAG + citations) | Placeholder | To do |
| Research Twin | Placeholder | To do |
| Knowledge Graph | Placeholder | To do |
| Landing page | To do | — |
