"""Comptes joueurs : hachage des mots de passe (pwdlib) et jetons JWT (PyJWT)."""

import logging
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import status
from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.errors import api_error, unauthorized
from app.models.player import Player

logger = logging.getLogger("dungeon.auth")

# Secret lu dans l'environnement ; la valeur par défaut ne sert qu'en développement
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-a-changer-en-production-0123456789")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hache un mot de passe."""
    return password_hash.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash."""
    return password_hash.verify(password, hashed)


def create_access_token(player_id: int) -> str:
    """Crée un JWT signé contenant l'id du joueur (claim sub) et une expiration."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({"sub": str(player_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


def register(session: Session, username: str, password: str) -> Player:
    """Crée un joueur ; 409 USERNAME_TAKEN si le nom est déjà pris."""
    if session.exec(select(Player).where(Player.username == username)).first() is not None:
        raise api_error(status.HTTP_409_CONFLICT, "USERNAME_TAKEN", f"Le nom d'utilisateur « {username} » est déjà pris.")
    player = Player(username=username, hashed_password=hash_password(password))
    session.add(player)
    session.commit()
    session.refresh(player)
    logger.info("Nouveau joueur inscrit : %s (#%s)", player.username, player.id)
    return player


def login(session: Session, username: str, password: str) -> str:
    """Renvoie un JWT si les identifiants sont bons, sinon 401 INVALID_CREDENTIALS."""
    player = session.exec(select(Player).where(Player.username == username)).first()
    if player is None or not verify_password(password, player.hashed_password):
        raise unauthorized("INVALID_CREDENTIALS", "Nom d'utilisateur ou mot de passe incorrect.")
    return create_access_token(player.id)


def get_player_from_token(session: Session, token: str | None) -> Player:
    """Décode le JWT et renvoie le joueur correspondant, sinon 401."""
    if not token:
        raise unauthorized("NOT_AUTHENTICATED", "Authentification requise : fournissez un token Bearer.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        player_id = int(payload["sub"])
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise unauthorized("INVALID_TOKEN", "Token invalide ou expiré.") from None
    player = session.get(Player, player_id)
    if player is None:
        raise unauthorized("INVALID_TOKEN", "Token invalide : joueur introuvable.")
    return player
