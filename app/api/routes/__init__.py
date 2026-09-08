from fastapi import APIRouter

from app.api.routes import accounts, ai, platform, players, statistics, teams

api_router = APIRouter()
api_router.include_router(players.router)
api_router.include_router(teams.router)
api_router.include_router(platform.router)
api_router.include_router(statistics.router)
api_router.include_router(ai.router)
api_router.include_router(accounts.router)
