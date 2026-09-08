"""Accounts: local users, session tokens, favorites, notification prefs.

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib only). Sessions are opaque
tokens. Favorites reference player/team/franchise ids verified against the
database. Notifications are derived from the platform event calendar — we never
invent events here.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models import Franchise, Player, Team, User
from app.models.user import Favorite, SessionToken, UserEventPref
from app.schemas.accounts import (
    FavoriteAdd,
    LoginRequest,
    PrefsUpdate,
    ProfileUpdate,
    RegisterRequest,
    user_out,
)

router = APIRouter(prefix="/api/account", tags=["accounts"])

_SESSION_DAYS = 30
_PBKDF2_ITERATIONS = 200_000
_KNOWN_EVENTS = ("preseason", "regular-season", "regular-season-end", "playoff-end")


def _hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _PBKDF2_ITERATIONS)
    return f"{_PBKDF2_ITERATIONS}${salt.hex()}$" + digest.hex()


def _verify_password(password: str, stored: str) -> bool:
    try:
        iterations, salt_hex, hash_hex = stored.split("$")
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except Exception:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
    return hmac.compare_digest(digest, expected)


def _new_token() -> tuple[str, datetime]:
    return secrets.token_urlsafe(48), datetime.now(UTC) + timedelta(days=_SESSION_DAYS)


async def _create_session(db: AsyncSession, user_id: int) -> str:
    token, expires = _new_token()
    db.add(SessionToken(token=token, user_id=user_id, expires_at=expires))
    await db.commit()
    return token


async def _current_user(
    authorization: str | None = Header(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in required.")
    token = authorization.split(" ", 1)[1].strip()
    st = (
        await db.execute(select(SessionToken).where(SessionToken.token == token))
    ).scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=401, detail="Session expired or not found.")
    if st.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        raise HTTPException(status_code=401, detail="Session expired.")
    user = await db.get(User, st.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Account not found.")
    return user


async def _favorites_of(db: AsyncSession, user_id: int) -> list[dict]:
    rows = (
        await db.execute(
            select(Favorite)
            .where(Favorite.user_id == user_id)
            .order_by(Favorite.item_type, Favorite.item_key)
        )
    ).scalars().all()
    return [
        {
            "id": f.id,
            "item_type": f.item_type,
            "item_key": f.item_key,
            "label": f.label,
        }
        for f in rows
    ]


async def _prefs_of(db: AsyncSession, user_id: int) -> list[dict]:
    rows = (
        await db.execute(
            select(UserEventPref).where(UserEventPref.user_id == user_id)
        )
    ).scalars().all()
    return [
        {
            "event_key": p.event_key,
            "lead_days": p.lead_days,
            "enabled": bool(p.enabled),
        }
        for p in rows
    ]


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    username = body.username.strip().lower()
    existing = (
        await db.execute(select(User).where(User.username == username))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="That username is taken.")
    user = User(
        username=username,
        display_name=(body.display_name or body.username).strip() or username,
        passkey_hash=_hash_password(body.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="That username is taken.")
    await db.refresh(user)
    token = await _create_session(db, user.id)
    return {"token": token, "user": user_out(user)}


@router.post("/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (
        await db.execute(select(User).where(User.username == body.username.strip().lower()))
    ).scalar_one_or_none()
    if user is None or not _verify_password(body.password, user.passkey_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password.")
    token = await _create_session(db, user.id)
    return {"token": token, "user": user_out(user)}


@router.post("/logout")
async def logout(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(None),
):
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
        await db.execute(delete(SessionToken).where(SessionToken.token == token))
        await db.commit()
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(_current_user), db: AsyncSession = Depends(get_db)):
    return {
        "user": user_out(user),
        "favorites": await _favorites_of(db, user.id),
        "prefs": await _prefs_of(db, user.id),
    }


@router.put("/me")
async def update_profile(
    body: ProfileUpdate,
    user: User = Depends(_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.display_name is not None:
        user.display_name = body.display_name.strip() or user.username
    await db.commit()
    return {"user": user_out(user)}


@router.delete("/me", status_code=204)
async def delete_account(user: User = Depends(_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(delete(SessionToken).where(SessionToken.user_id == user.id))
    await db.execute(delete(Favorite).where(Favorite.user_id == user.id))
    await db.execute(delete(UserEventPref).where(UserEventPref.user_id == user.id))
    await db.delete(user)
    await db.commit()
    return None


@router.get("/favorites")
async def favorites(user: User = Depends(_current_user), db: AsyncSession = Depends(get_db)):
    return {"favorites": await _favorites_of(db, user.id)}


@router.post("/favorites", status_code=201)
async def add_favorite(
    body: FavoriteAdd,
    user: User = Depends(_current_user),
    db: AsyncSession = Depends(get_db),
):
    model = {"player": Player, "team": Team, "franchise": Franchise}[body.item_type]
    exists = await db.get(model, body.item_key)
    if exists is None:
        raise HTTPException(status_code=404, detail=f"No such {body.item_type}.")
    if body.item_type == "player":
        label = body.label or getattr(exists, "full_name", None) or str(body.item_key)
    else:
        label = (
            body.label
            or getattr(exists, "full_name", None)
            or getattr(exists, "name", None)
            or str(body.item_key)
        )
    row = (
        await db.execute(
            select(Favorite).where(
                Favorite.user_id == user.id,
                Favorite.item_type == body.item_type,
                Favorite.item_key == body.item_key,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        db.add(
            Favorite(
                user_id=user.id,
                item_type=body.item_type,
                item_key=body.item_key,
                label=label,
            )
        )
    else:
        row.label = label
    await db.commit()
    return {"favorites": await _favorites_of(db, user.id)}


@router.delete("/favorites/{item_type}/{item_key}")
async def remove_favorite(
    item_type: str,
    item_key: int,
    user: User = Depends(_current_user),
    db: AsyncSession = Depends(get_db),
):
    await db.execute(
        delete(Favorite).where(
            Favorite.user_id == user.id,
            Favorite.item_type == item_type,
            Favorite.item_key == item_key,
        )
    )
    await db.commit()
    return {"favorites": await _favorites_of(db, user.id)}


@router.get("/notifications")
async def notifications(
    user: User = Depends(_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upcoming events your prefs asked for, within the lead window."""
    from app.api.routes.platform import _events_payload

    calendar = await _events_payload(db)
    prefs = await _prefs_of(db, user.id)
    out: list[dict] = []
    for pref in prefs:
        if not pref["enabled"]:
            continue
        ev = next((e for e in calendar["events"] if e["id"] == pref["event_key"]), None)
        if ev is None or ev.get("is_past") or ev.get("countdown_seconds") is None:
            continue
        lead = timedelta(days=pref["lead_days"]).total_seconds()
        cd = ev["countdown_seconds"]
        if cd <= lead:
            out.append(
                {
                    "event_key": pref["event_key"],
                    "title": ev["title"],
                    "date": ev.get("date"),
                    "source": ev.get("source"),
                    "lead_days": pref["lead_days"],
                    "days_until": round(cd / 86400, 1),
                }
            )
    out.sort(key=lambda n: n["days_until"])
    return {"notifications": out}


@router.get("/prefs")
async def prefs(user: User = Depends(_current_user), db: AsyncSession = Depends(get_db)):
    return {"prefs": await _prefs_of(db, user.id)}


@router.put("/prefs")
async def update_prefs(
    body: PrefsUpdate,
    user: User = Depends(_current_user),
    db: AsyncSession = Depends(get_db),
):
    keys = [k for k in body.event_keys if k in _KNOWN_EVENTS]
    rows = (
        await db.execute(
            select(UserEventPref).where(UserEventPref.user_id == user.id)
        )
    ).scalars().all()
    by_key = {p.event_key: p for p in rows}
    for key in _KNOWN_EVENTS:
        pref = by_key.get(key)
        enabled = key in keys
        if pref is None:
            db.add(
                UserEventPref(
                    user_id=user.id,
                    event_key=key,
                    lead_days=body.lead_days,
                    enabled=1 if enabled else 0,
                )
            )
        else:
            pref.enabled = 1 if enabled else 0
            pref.lead_days = body.lead_days
    await db.commit()
    return {"prefs": await _prefs_of(db, user.id)}
