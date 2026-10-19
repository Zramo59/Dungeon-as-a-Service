"""Schémas transverses : format d'erreur, santé, classement."""

from pydantic import BaseModel


class ErrorDetail(BaseModel):
    """Contenu de `detail` pour toutes les erreurs métier."""

    error: str
    message: str


class ErrorResponse(BaseModel):
    """Corps d'une erreur métier (400, 401, 403, 404, 409)."""

    detail: ErrorDetail


class HealthRead(BaseModel):
    """Réponse de GET /health."""

    status: str
    message: str


class LeaderboardEntry(BaseModel):
    """Une ligne du classement public."""

    rang: int
    nom: str
    classe: str
    joueur: str
    or_: int
    victoire: bool


def error_doc(description: str) -> dict:
    """Entrée `responses=` documentant une erreur métier dans Swagger."""
    return {"model": ErrorResponse, "description": description}
