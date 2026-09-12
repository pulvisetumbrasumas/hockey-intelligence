"""Unit tests for the live news feed normalizer."""

from app.api.routes.platform import (
    _normalize_espn_news,
    _partition_retired,
)


async def test_normalize_espn_news_flattens_articles():
    payload = {
        "articles": [
            {
                "id": 49913580,
                "headline": "Star winger signs three-year deal",
                "description": "The veteran forward agreed to terms on a new contract today.",
                "byline": "Jane Reporter",
                "published": "2026-09-12T14:52:10Z",
                "premium": False,
                "type": "HeadlineNews",
                "categories": [
                    {"id": 9580, "type": "league", "description": "NHL"},
                    {"id": 900, "type": "tag", "description": "Transactions"},
                ],
                "images": [
                    {
                        "type": "header",
                        "url": "https://a.espncdn.com/photo/foo.jpg",
                        "height": 400,
                        "width": 600,
                    }
                ],
                "links": {
                    "web": {"href": "https://www.espn.com/nhl/story/_/id/49913580"},
                },
                "contentKey": "foo",
            },
            {
                "id": 49913581,
                "headline": "No image and no link",
                "description": None,
                "byline": "",
                "published": None,
                "premium": True,
                "categories": [],
                "images": [],
                "links": {"api": {"self": {"href": "https://api"}}},
            },
        ]
    }

    out = await _normalize_espn_news(payload)

    assert len(out) == 2
    a = out[0]
    assert a["id"] == 49913580
    assert a["title"] == "Star winger signs three-year deal"
    assert a["category"] == "NHL"
    assert a["tags"] == ["NHL", "Transactions"]
    assert a["image"] == "https://a.espncdn.com/photo/foo.jpg"
    assert a["link"] == "https://www.espn.com/nhl/story/_/id/49913580"
    assert a["premium"] is False

    b = out[1]
    assert b["image"] == ""
    assert b["link"] == ""
    assert b["category"] == "NHL"
    assert b["premium"] is True


async def test_normalize_espn_news_empty():
    assert await _normalize_espn_news({"articles": []}) == []
    assert await _normalize_espn_news({}) == []


def test_partition_retired_splits_candidates():
    free = [{"player_id": 1}, {"player_id": 2}, {"player_id": 3}, {"player_id": 4}]
    landed_off = {1: True, 3: True}

    free_agents, retired = _partition_retired(free, landed_off)

    assert [p["player_id"] for p in free_agents] == [2, 4]
    assert [p["player_id"] for p in retired] == [1, 3]
    # order within each bucket follows the candidate order
    assert free_agents[0]["player_id"] == 2
    # untouched windows: unknown status stays with the free agents
    assert all(p["player_id"] not in landed_off for p in free_agents)