"""Dépendances partagées par les routers : session de base et joueur connecté."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from app.database import get_session
from app.models.player import Player
from app.services import auth_service

# auto_error=False : on renvoie nous-mêmes un 401 au format imposé
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

SessionDep = Annotated[Session, Depends(get_session)]


def get_current_player(session: SessionDep, token: Annotated[str | None, Depends(oauth2_scheme)]) -> Player:
    """Joueur authentifié par le token Bearer (401 sinon)."""
    return auth_service.get_player_from_token(session, token)


CurrentPlayer = Annotated[Player, Depends(get_current_player)]
