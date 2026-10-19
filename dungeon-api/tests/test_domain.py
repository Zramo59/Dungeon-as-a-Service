"""Tests unitaires des classes métier (sans FastAPI ni base)."""

import pytest

from app.domain.combat import HEROS_MORT, MONSTRE_VAINCU, jouer_tour
from app.domain.heros import CLASSES_HEROS, Guerrier, Heros, Mage, Voleur, creer_heros
from scripts.simulation import HEROS_TESTES, simuler


def test_heros_est_abstrait() -> None:
    with pytest.raises(TypeError):
        Heros(5, 3, 2)  # type: ignore[abstract]


def test_pv_max_et_degats() -> None:
    g = Guerrier(6, 2, 2)
    assert g.pv_max == 32
    assert g.calculer_degats() == (14, False)
    assert g.subir_degats(4) == 3
    assert g.subir_degats(1) == 1  # minimum 1

    m = Mage(2, 2, 6)
    assert m.pv_max == 24
    assert m.calculer_degats() == (19, False)
    assert m.subir_degats(4) == 4  # comportement hérité


def test_voleur_critique_injectable() -> None:
    assert Voleur(2, 6, 2, alea=lambda: 0.0).calculer_degats() == (28, True)
    assert Voleur(2, 6, 2, alea=lambda: 0.5).calculer_degats() == (14, False)
    assert Voleur(2, 6, 2).subir_degats(5) == 5


def test_fabrique() -> None:
    for classe, cls in CLASSES_HEROS.items():
        assert type(creer_heros(classe, 4, 3, 3)) is cls


def test_jouer_tour() -> None:
    g = Guerrier(6, 2, 2)
    tour = jouer_tour(g, 32, 30, 6)
    assert (tour.degats_infliges, tour.degats_subis, tour.pv_heros, tour.pv_monstre) == (14, 5, 27, 16)
    assert jouer_tour(g, 32, 10, 6).issue == MONSTRE_VAINCU
    assert jouer_tour(g, 3, 30, 6).issue == HEROS_MORT


@pytest.mark.parametrize("classe,pv_restants", [("guerrier", 14), ("mage", 10), ("voleur", 3)])
def test_equilibrage_chaque_classe_bat_la_liche(classe: str, pv_restants: int) -> None:
    """Stat principale 6 + un repos avant la salle du trône : victoire garantie (cf. README)."""
    victoire, pv, _ = simuler(HEROS_TESTES[classe])
    assert victoire and pv == pv_restants
