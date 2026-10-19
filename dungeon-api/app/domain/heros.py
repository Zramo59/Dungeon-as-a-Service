"""Héros du donjon : une classe abstraite et trois classes concrètes.

Aucune dépendance à FastAPI ni à la base : ces classes sont testables seules.
"""

import random
from abc import ABC, abstractmethod
from collections.abc import Callable


class Heros(ABC):
    """Héros abstrait : porte les stats et les règles communes."""

    def __init__(self, force: int, agilite: int, intelligence: int) -> None:
        self.force = force
        self.agilite = agilite
        self.intelligence = intelligence

    @property
    def pv_max(self) -> int:
        """PV maximum : 20 + force x 2."""
        return 20 + self.force * 2

    @abstractmethod
    def calculer_degats(self) -> tuple[int, bool]:
        """Renvoie (dégâts infligés, coup critique ?)."""

    def subir_degats(self, attaque_monstre: int) -> int:
        """Dégâts réellement subis face à une attaque (par défaut : l'attaque du monstre)."""
        return attaque_monstre


class Guerrier(Heros):
    """Frappe fort et encaisse : 1 point d'armure."""

    def calculer_degats(self) -> tuple[int, bool]:
        return 2 + self.force * 2, False

    def subir_degats(self, attaque_monstre: int) -> int:
        return max(1, attaque_monstre - 1)


class Mage(Heros):
    """Dégâts basés sur l'intelligence."""

    def calculer_degats(self) -> tuple[int, bool]:
        return 1 + self.intelligence * 3, False


class Voleur(Heros):
    """Dégâts basés sur l'agilité, coup critique (x2) une fois sur trois."""

    CHANCE_CRITIQUE = 1 / 3

    def __init__(
        self,
        force: int,
        agilite: int,
        intelligence: int,
        alea: Callable[[], float] = random.random,
    ) -> None:
        super().__init__(force, agilite, intelligence)
        # alea renvoie un flottant dans [0, 1[ ; injectable pour rendre les tests déterministes
        self.alea = alea

    def calculer_degats(self) -> tuple[int, bool]:
        degats = 2 + self.agilite * 2
        critique = self.alea() < self.CHANCE_CRITIQUE
        return (degats * 2 if critique else degats), critique


# Fabrique : nom de classe -> sous-classe (évite tout if sur la classe dans les services)
CLASSES_HEROS: dict[str, type[Heros]] = {
    "guerrier": Guerrier,
    "mage": Mage,
    "voleur": Voleur,
}


def creer_heros(classe: str, force: int, agilite: int, intelligence: int) -> Heros:
    """Construit l'objet métier correspondant à la classe donnée."""
    return CLASSES_HEROS[classe](force, agilite, intelligence)
