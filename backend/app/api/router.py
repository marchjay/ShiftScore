from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import auth, bartenders, bars, dev, leaderboard, shifts, spots, users


api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(dev.router, tags=["dev"])
api_router.include_router(bars.router, tags=["bars"])
api_router.include_router(leaderboard.router, tags=["leaderboard"])
api_router.include_router(spots.router, tags=["spots"])
api_router.include_router(bartenders.router, tags=["bartenders"])
api_router.include_router(shifts.router, tags=["shifts"])
api_router.include_router(users.router, tags=["users"])
