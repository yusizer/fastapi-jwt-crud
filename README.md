# FastAPI JWT CRUD API 🔐

A production-style REST API: **JWT authentication** (register, login, refresh) and
**full CRUD for posts** with owner-only update/delete. Auto-generated **Swagger UI**
as the live demo. PostgreSQL-ready, Dockerized, tested.

> **Live demo (Swagger UI):** _<добавь Railway-домен>/docs_ ·
> **Source:** https://github.com/yusizer/fastapi-jwt-crud

## Features

- **Auth**: register, login (OAuth2 password flow), refresh tokens, `/auth/me`.
  Access token (short-lived) + refresh token (long-lived), HS256 JWT, bcrypt-hashed passwords.
- **Posts CRUD**: create / list / get / update / delete. Update & delete are
  **owner-only** (403 for other users).
- **Validation**: Pydantic v2 (email format, min password length, field constraints).
- **DB**: SQLAlchemy 2 async — **SQLite** for local dev, **PostgreSQL** for production
  (one config switch via `DATABASE_URL`).
- **Tests**: pytest + httpx async, 20+ end-to-end cases (auth, CRUD, owner permissions, bad tokens).
- **Swagger UI** auto-generated at `/docs`, ReDoc at `/redoc`.
- **Healthcheck** at `/health`.

## Stack

| Layer     | Technology                                  |
|-----------|---------------------------------------------|
| API       | FastAPI 0.115                               |
| Auth      | PyJWT (HS256) + passlib/bcrypt              |
| DB        | SQLAlchemy 2 (async) + aiosqlite / asyncpg  |
| Validation| Pydantic v2                                 |
| Tests     | pytest, httpx, pytest-asyncio               |
| Deploy    | Docker → Railway                            |

## Structure

```
fastapi-jwt-crud/
├── app/
│   ├── __main__.py     # entrypoint (uvicorn)
│   ├── config.py       # settings from .env
│   ├── models.py       # User, Post
│   ├── database.py     # async engine + get_db dependency
│   ├── schemas.py      # Pydantic request/response models
│   ├── security.py     # bcrypt + JWT helpers
│   ├── deps.py         # get_current_user dependency
│   └── main.py         # FastAPI app + routes
├── tests/
│   ├── conftest.py     # in-memory DB + ASGI client fixtures
│   └── test_api.py     # end-to-end tests
├── requirements.txt
├── Dockerfile
├── pytest.ini
└── .env.example
```

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env   # Windows: copy .env.example .env
# set JWT_SECRET to a long random string

python -m app
```

- Swagger UI: http://localhost:8000/docs
- ReDoc:      http://localhost:8000/redoc
- Health:     http://localhost:8000/health

### Quick try in Swagger UI

1. `POST /auth/register` → `{"email": "you@example.com", "password": "supersecret123"}`
2. `POST /auth/login` → click **Authorize** in Swagger, or send form: `username=you@example.com&password=supersecret123`
3. Copy `access_token`, click **Authorize** 🔒, paste `Bearer <token>`
4. `POST /posts`, `GET /posts`, `PUT /posts/{id}`, `DELETE /posts/{id}`

## Run tests

```bash
pip install -r requirements.txt
pytest -v
```

## Deploy to Railway

1. Push the repo to GitHub.
2. https://railway.app → **New Project → Deploy from GitHub repo** → select this repo.
3. Railway auto-detects the `Dockerfile`.
4. **Variables**:
   - `JWT_SECRET` — long random string
   - `DATABASE_URL` — from a Railway **PostgreSQL** provisioned database
     (`postgresql+asyncpg://...`). Add a Postgres database in the project and use its connection string.
5. Railway sets `PORT` automatically — the app reads it.
6. Open the public domain → `/docs` is your live Swagger demo link for the portfolio.

## API reference (summary)

| Method | Path                | Auth | Description              |
|--------|---------------------|------|--------------------------|
| POST   | /auth/register      | —    | Create a user            |
| POST   | /auth/login         | —    | Get access + refresh     |
| POST   | /auth/refresh       | —    | Refresh access token     |
| GET    | /auth/me            | ✅   | Current user             |
| POST   | /posts              | ✅   | Create a post            |
| GET    | /posts              | —    | List all posts           |
| GET    | /posts/{id}         | —    | Get one post             |
| PUT    | /posts/{id}         | ✅   | Update (owner only)      |
| DELETE | /posts/{id}         | ✅   | Delete (owner only)      |
| GET    | /health             | —    | Health check             |

## Screenshots

| Swagger UI | Auth flow |
|:---:|:---:|
| ![swagger](docs/swagger.png) | ![auth](docs/auth.png) |

_Drop screenshots in `docs/` after running._
