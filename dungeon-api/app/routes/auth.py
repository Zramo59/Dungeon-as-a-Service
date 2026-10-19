"""Routes d'authentification : inscription et connexion."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.routes.dependencies import SessionDep
from app.schemas.auth import PlayerCreate, PlayerRead, Token
from app.schemas.common import error_doc
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post(
    "/register",
    response_model=PlayerRead,
    status_code=status.HTTP_201_CREATED,
    responses={409: error_doc("USERNAME_TAKEN : nom d'utilisateur déjà pris")},
)
def register(data: PlayerCreate, session: SessionDep) -> PlayerRead:
    """Crée un compte joueur."""
    player = auth_service.register(session, data.username, data.password)
    return PlayerRead(id=player.id, username=player.username)


@router.post(
    "/login",
    response_model=Token,
    responses={401: error_doc("INVALID_CREDENTIALS : identifiants incorrects")},
)
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> Token:
    """Connexion (formulaire OAuth2) : renvoie un token JWT Bearer."""
    return Token(access_token=auth_service.login(session, form.username, form.password))
