"""FastAPI application: JWT auth + posts CRUD."""
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import get_db, init_db
from .deps import get_current_user
from .models import Post, User
from .schemas import (
    PostCreate,
    PostOut,
    PostUpdate,
    RefreshIn,
    Token,
    UserCreate,
    UserOut,
)
from .security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)

app = FastAPI(
    title="FastAPI JWT CRUD",
    description="JWT authentication + posts CRUD. Auto-generated Swagger UI at /docs.",
    version="1.0.0",
)


@app.on_event("startup")
async def _on_startup() -> None:
    await init_db()


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------- Auth ----------------

@app.post("/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=payload.email, hashed_password=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@app.post("/auth/login", response_model=Token)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # OAuth2 form uses `username` field — we put the email there.
    result = await db.execute(select(User).where(User.email == form.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@app.post("/auth/refresh", response_model=Token)
async def refresh(payload: RefreshIn, db: AsyncSession = Depends(get_db)):
    try:
        decoded = decode_token(payload.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    user = await db.get(User, int(decoded["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return Token(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@app.get("/auth/me", response_model=UserOut)
async def me(current: User = Depends(get_current_user)):
    return current


# ---------------- Posts ----------------

@app.post("/posts", response_model=PostOut, status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = Post(title=payload.title, content=payload.content, owner_id=current.id)
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


@app.get("/posts", response_model=list[PostOut])
async def list_posts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Post).order_by(Post.created_at.desc()))
    return result.scalars().all()


@app.get("/posts/{post_id}", response_model=PostOut)
async def get_post(post_id: int, db: AsyncSession = Depends(get_db)):
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    return post


@app.put("/posts/{post_id}", response_model=PostOut)
async def update_post(
    post_id: int,
    payload: PostUpdate,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.owner_id != current.id:
        raise HTTPException(status_code=403, detail="Not the owner")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(post, key, value)
    await db.commit()
    await db.refresh(post)
    return post


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = await db.get(Post, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.owner_id != current.id:
        raise HTTPException(status_code=403, detail="Not the owner")
    await db.delete(post)
    await db.commit()
