from fastapi import APIRouter

from app.api.routes import ai, platform, players, statistics, teams

api_router = APIRouter()
api_router.include_router(players.router)
api_router.include_router(teams.router)
api_router.include_router(platform.router)
api_router.include_router(statistics.router)
api_router.include_router(ai.router)
