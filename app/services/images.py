"""Deterministic NHL media URL builders.

Image URLs are derived purely from database values (abbreviation, NHL player
id) and the current NHL media-season key. No calls are made to the API from
here; these are stable asset links that the browser resolves directly.
"""
from __future__ import annotations

from app.core.config import get_settings


def _assets() -> str:
    return get_settings().nhl_assets_base


def team_logo_url(abbreviation: str | None, variant: str = "light") -> str | None:
    if not abbreviation:
        return None
    return f"{_assets()}/logos/nhl/svg/{abbreviation.upper()}_{variant}.svg"


def player_headshot_url(
    player_id: int | None, team_abbreviation: str | None
) -> str | None:
    if not player_id or not team_abbreviation:
        return None
    season = get_settings().nhl_media_season
    return f"{_assets()}/mugs/nhl/{season}/{team_abbreviation.upper()}/{player_id}.png"


def player_hero_url(player_id: int | None) -> str | None:
    if not player_id:
        return None
    return f"{_assets()}/mugs/actionshots/1296x729/{player_id}.jpg"
