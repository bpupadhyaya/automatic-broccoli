# AI YouTube Remix Generator (MVP)

Production-style MVP web application that generates a **remix music video project plan** from three YouTube URLs.

This version does **not** generate actual video media. It generates planning assets only:
- remix transformation summary
- fictional character bible
- storyboard scenes
- AI scene prompts
- editing plan
- consistency rules
- final manifest JSON

## Repository Structure

```text
backend/   FastAPI + SQLAlchemy + Alembic + PostgreSQL
frontend/  React + Vite + TypeScript + Tailwind CSS
docker-compose.yml  Containerized deployment (frontend + backend + postgres)
```

## Tech Stack

- Frontend: React, Vite, TypeScript, React Router, Tailwind CSS
- Backend: FastAPI, Pydantic v2, SQLAlchemy ORM, Alembic
- Database: PostgreSQL

## Safety

By default, `celebrity_mode` is `fictional_only`.

The system includes explicit safety guidance that cloning real celebrity likeness requires rights/licensing. Do not use this project for unauthorized identity replication.

## Backend Setup

1. Go to backend:

```bash
cd backend
```

2. Create env file:

```bash
cp .env.example .env
```

3. Create and activate venv:

```bash
python -m venv venv
source venv/bin/activate
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run migrations:

```bash
alembic upgrade head
```

6. Start API:

```bash
uvicorn app.main:app --reload
```

Backend default URL: `http://localhost:8000`

## Frontend Setup

1. Go to frontend:

```bash
cd frontend
```

2. Install dependencies:

```bash
npm install
```

3. Start app:

```bash
npm run dev
```

Frontend default URL: `http://localhost:5173`

If backend runs on a custom URL, set:

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

## Build And Deploy (Docker)

Run from repository root:

```bash
docker compose up -d --build
```

Deployed services:

- Frontend: `http://localhost:5179`
- Backend API: `http://localhost:18082`
- Backend health: `http://localhost:18082/health`
- PostgreSQL: `localhost:55442` (`user/password`, db: `remixdb`)

Stop deployment:

```bash
docker compose down
```

## Database Configuration

Set this in `backend/.env`:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/remixdb
```

## API Endpoints

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `POST /api/projects/{project_id}/generate-plan`
- `GET /api/projects/{project_id}/manifest`

Additional utility endpoint:

- `GET /health`

## Error Handling

- Validation errors: HTTP `400`
- Not found: HTTP `404`
- Unhandled errors: HTTP `500`

All responses are JSON.

## Notes on Extensibility

`manifest.future_extensions.video_generation_engines` includes placeholders for future integration with real generation engines.

The current MVP keeps generation deterministic and mock-based to simplify local development and testing.
