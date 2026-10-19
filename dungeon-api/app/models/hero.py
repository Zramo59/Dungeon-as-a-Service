"""Table des héros."""

from sqlmodel import Field, SQLModel


class Hero(SQLModel, table=True):
    """Un héros tel qu'il est stocké en base.

    monstre_pv vaut None hors combat, sinon les PV restants du monstre de la salle.
    monstre_pv et owner_id ne sont jamais exposés : voir HeroRead.
    """

    id: int | None = Field(default=None, primary_key=True)
    nom: str
    classe: str
    force: int
    agilite: int
    intelligence: int
    pv: int
    pv_max: int
    salle_actuelle: str
    or_: int = 0
    monstre_pv: int | None = None
    victoire: bool = False
    owner_id: int = Field(foreign_key="player.id", index=True)
