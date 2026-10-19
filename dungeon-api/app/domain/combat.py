"""Règles d'un tour de combat, indépendantes de FastAPI et de la base."""

from dataclasses import dataclass

from app.domain.heros import Heros

EN_COURS = "en_cours"
MONSTRE_VAINCU = "monstre_vaincu"
HEROS_MORT = "heros_mort"


@dataclass(frozen=True)
class ResultatTour:
    """Ce qui s'est passé pendant un tour."""

    degats_infliges: int
    critique: bool
    degats_subis: int
    pv_heros: int
    pv_monstre: int
    issue: str


def jouer_tour(heros: Heros, pv_heros: int, pv_monstre: int, attaque_monstre: int) -> ResultatTour:
    """Le héros frappe en premier ; si le monstre survit, il riposte."""
    degats, critique = heros.calculer_degats()
    pv_monstre = max(0, pv_monstre - degats)
    if pv_monstre == 0:
        return ResultatTour(degats, critique, 0, pv_heros, 0, MONSTRE_VAINCU)

    subis = heros.subir_degats(attaque_monstre)
    pv_heros = max(0, pv_heros - subis)
    issue = HEROS_MORT if pv_heros == 0 else EN_COURS
    return ResultatTour(degats, critique, subis, pv_heros, pv_monstre, issue)
