"""Routes publiques (sans authentification) : santé et classement."""

from fastapi import APIRouter

from app.routes.dependencies import SessionDep
from app.schemas.common import HealthRead, LeaderboardEntry
from app.services import leaderboard_service

router = APIRouter()


@router.get("/health", response_model=HealthRead, tags=["Système"])
def health() -> HealthRead:
    """Vérifie que le serveur répond."""
    return HealthRead(status="ok", message="Le donjon vous attend...")


@router.get("/leaderboard", response_model=list[LeaderboardEntry], tags=["Classement"])
def leaderboard(session: SessionDep) -> list[LeaderboardEntry]:
    """Top 10 public : victoires d'abord, puis or décroissant."""
    return leaderboard_service.get_leaderboard(session)
