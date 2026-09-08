import pytest

from app.api.routes.accounts import _hash_password, _verify_password
from app.models import User


def test_password_hashing_roundtrip():
    h = _hash_password("correct horse battery staple")
    assert _verify_password("correct horse battery staple", h)
    assert not _verify_password("wrong", h)


@pytest.mark.asyncio
async def test_user_creation(session):
    user = User(username="fan22", display_name="Fan 22", passkey_hash=_hash_password("pw1234"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    assert user.id is not None
    assert user.username == "fan22"


@pytest.mark.asyncio
async def test_favorite_unique_constraint(session):
    from app.models import Favorite

    user = User(username="a", passkey_hash=_hash_password("x6"))
    session.add(user)
    await session.flush()
    session.add(Favorite(user_id=user.id, item_type="player", item_key=8478402, label="McDavid"))
    await session.flush()
    dup = Favorite(user_id=user.id, item_type="player", item_key=8478402, label="Dup")
    session.add(dup)
    with pytest.raises(Exception):
        await session.flush()
    await session.rollback()
