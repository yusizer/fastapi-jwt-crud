"""End-to-end API tests against the ASGI app (in-memory DB)."""
import pytest

pytestmark = pytest.mark.asyncio

EMAIL = "alice@example.com"
PASSWORD = "supersecret123"


def _bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _register_and_login(client, email=EMAIL, password=PASSWORD):
    await client.post("/auth/register", json={"email": email, "password": password})
    r = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    assert r.status_code == 200
    return r.json()


# --- Auth ---

async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_register_creates_user(client):
    r = await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 201
    data = r.json()
    assert data["email"] == EMAIL
    assert "id" in data and "hashed_password" not in data


async def test_register_duplicate_rejected(client):
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    r = await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    assert r.status_code == 409


async def test_register_short_password_rejected(client):
    r = await client.post("/auth/register", json={"email": "x@y.com", "password": "short"})
    assert r.status_code == 422


async def test_login_wrong_password(client):
    await client.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    r = await client.post("/auth/login", data={"username": EMAIL, "password": "wrongpass"})
    assert r.status_code == 401


async def test_login_returns_tokens(client):
    tokens = await _register_and_login(client)
    assert tokens["token_type"] == "bearer"
    assert tokens["access_token"]
    assert tokens["refresh_token"]


async def test_me_requires_auth(client):
    r = await client.get("/auth/me")
    assert r.status_code == 401


async def test_me_returns_user(client):
    tokens = await _register_and_login(client)
    r = await client.get("/auth/me", headers=_bearer(tokens["access_token"]))
    assert r.status_code == 200
    assert r.json()["email"] == EMAIL


async def test_refresh_issues_new_access(client):
    tokens = await _register_and_login(client)
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


async def test_refresh_rejects_access_token(client):
    tokens = await _register_and_login(client)
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["access_token"]})
    assert r.status_code == 401


async def test_invalid_token_rejected(client):
    r = await client.get("/auth/me", headers=_bearer("not-a-jwt"))
    assert r.status_code == 401


# --- Posts CRUD ---

async def test_create_post_requires_auth(client):
    r = await client.post("/posts", json={"title": "Hi", "content": "body"})
    assert r.status_code == 401


async def test_create_and_list_post(client):
    tokens = await _register_and_login(client)
    r = await client.post(
        "/posts",
        json={"title": "First post", "content": "Hello world"},
        headers=_bearer(tokens["access_token"]),
    )
    assert r.status_code == 201
    post = r.json()
    assert post["title"] == "First post"
    assert post["content"] == "Hello world"

    r2 = await client.get("/posts")
    assert r2.status_code == 200
    assert len(r2.json()) == 1


async def test_get_single_post(client):
    tokens = await _register_and_login(client)
    r = await client.post(
        "/posts", json={"title": "T", "content": "C"}, headers=_bearer(tokens["access_token"])
    )
    pid = r.json()["id"]
    r2 = await client.get(f"/posts/{pid}")
    assert r2.status_code == 200
    assert r2.json()["id"] == pid


async def test_get_missing_post_404(client):
    r = await client.get("/posts/9999")
    assert r.status_code == 404


async def test_update_own_post(client):
    tokens = await _register_and_login(client)
    r = await client.post(
        "/posts", json={"title": "Old", "content": "old"}, headers=_bearer(tokens["access_token"])
    )
    pid = r.json()["id"]
    r2 = await client.put(
        f"/posts/{pid}",
        json={"title": "New title"},
        headers=_bearer(tokens["access_token"]),
    )
    assert r2.status_code == 200
    assert r2.json()["title"] == "New title"
    assert r2.json()["content"] == "old"  # unchanged


async def test_update_other_users_post_forbidden(client):
    a = await _register_and_login(client, "a@x.com", "password123")
    b = await _register_and_login(client, "b@x.com", "password123")
    r = await client.post(
        "/posts", json={"title": "A's post", "content": "c"}, headers=_bearer(a["access_token"])
    )
    pid = r.json()["id"]
    r2 = await client.put(
        f"/posts/{pid}", json={"title": "hacked"}, headers=_bearer(b["access_token"])
    )
    assert r2.status_code == 403


async def test_delete_own_post(client):
    tokens = await _register_and_login(client)
    r = await client.post(
        "/posts", json={"title": "Bye", "content": "c"}, headers=_bearer(tokens["access_token"])
    )
    pid = r.json()["id"]
    r2 = await client.delete(f"/posts/{pid}", headers=_bearer(tokens["access_token"]))
    assert r2.status_code == 204
    r3 = await client.get(f"/posts/{pid}")
    assert r3.status_code == 404


async def test_delete_other_users_post_forbidden(client):
    a = await _register_and_login(client, "a@x.com", "password123")
    b = await _register_and_login(client, "b@x.com", "password123")
    r = await client.post(
        "/posts", json={"title": "A's post", "content": "c"}, headers=_bearer(a["access_token"])
    )
    pid = r.json()["id"]
    r2 = await client.delete(f"/posts/{pid}", headers=_bearer(b["access_token"]))
    assert r2.status_code == 403
