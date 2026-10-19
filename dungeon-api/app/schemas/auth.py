"""Schémas d'authentification."""

from pydantic import BaseModel, ConfigDict, Field


class PlayerCreate(BaseModel):
    """Corps de POST /auth/register."""

    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(min_length=3, max_length=30, examples=["alice"])
    password: str = Field(min_length=4, max_length=128, examples=["secret"])


class PlayerRead(BaseModel):
    """Joueur renvoyé par l'API (sans le mot de passe)."""

    id: int
    username: str


class Token(BaseModel):
    """Réponse de POST /auth/login."""

    access_token: str
    token_type: str = "bearer"
