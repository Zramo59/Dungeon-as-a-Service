"""Erreurs métier au format imposé : {"detail": {"error": "CODE", "message": "..."}}."""

from fastapi import HTTPException, status


def api_error(status_code: int, code: str, message: str, headers: dict[str, str] | None = None) -> HTTPException:
    """Construit une HTTPException dont le detail respecte le format du sujet."""
    return HTTPException(
        status_code=status_code,
        detail={"error": code, "message": message},
        headers=headers,
    )


def unauthorized(code: str, message: str) -> HTTPException:
    """401 avec l'en-tête WWW-Authenticate attendu par OAuth2."""
    return api_error(status.HTTP_401_UNAUTHORIZED, code, message, {"WWW-Authenticate": "Bearer"})
