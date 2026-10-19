"""Table des joueurs (comptes)."""

from sqlmodel import Field, SQLModel


class Player(SQLModel, table=True):
    """Un joueur : identifiant unique et mot de passe haché (jamais en clair)."""

    id: int | None = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True, max_length=30)
    hashed_password: str
