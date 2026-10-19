"""Schémas d'entrée/sortie des héros, des salles et du combat."""

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

SOMME_STATS = 10

# Une stat est un entier STRICT (ni "5", ni 5.0) compris entre 1 et 8
Stat = Annotated[int, Field(strict=True, ge=1, le=8)]


class ClasseHeros(str, Enum):
    """Classes jouables."""

    guerrier = "guerrier"
    mage = "mage"
    voleur = "voleur"


class Direction(str, Enum):
    """Directions de déplacement."""

    nord = "nord"
    sud = "sud"
    est = "est"
    ouest = "ouest"


class HeroCreate(BaseModel):
    """Corps de POST /heroes : toute la validation est faite ici (422 sinon)."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        json_schema_extra={
            "examples": [
                {"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2}
            ]
        },
    )

    nom: str = Field(min_length=3, max_length=20)
    classe: ClasseHeros
    force: Stat
    agilite: Stat
    intelligence: Stat

    @model_validator(mode="after")
    def verifier_somme(self) -> "HeroCreate":
        """La somme des trois stats doit valoir exactement 10."""
        total = self.force + self.agilite + self.intelligence
        if total != SOMME_STATS:
            raise ValueError(
                f"La somme force + agilite + intelligence doit valoir exactement {SOMME_STATS} (reçu {total})."
            )
        return self


class HeroRead(BaseModel):
    """Héros renvoyé par l'API : ni monstre_pv ni owner_id, mais en_combat et est_vivant."""

    id: int
    nom: str
    classe: str
    force: int
    agilite: int
    intelligence: int
    pv: int
    pv_max: int
    salle_actuelle: str
    or_: int
    victoire: bool
    en_combat: bool
    est_vivant: bool


class MoveRequest(BaseModel):
    """Corps de POST /heroes/{id}/move."""

    direction: Direction


class MonsterRead(BaseModel):
    """Monstre présent dans la salle pendant un combat."""

    id: str
    nom: str
    pv: int
    pv_max: int
    attaque: int


class RoomRead(BaseModel):
    """Salle où se trouve le héros."""

    id: str
    nom: str
    description: str
    sorties: dict[str, str]
    monstre: MonsterRead | None = None


class AttackResult(BaseModel):
    """Résultat d'un tour de combat (format exact du sujet)."""

    degats_infliges: int
    critique: bool
    degats_subis: int
    pv_heros: int
    pv_monstre: int
    issue: Literal["en_cours", "monstre_vaincu", "heros_mort"]
    or_gagne: int
    victoire: bool
