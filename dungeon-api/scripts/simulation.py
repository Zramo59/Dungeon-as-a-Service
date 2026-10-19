"""Simulation d'équilibrage : chaque classe (stat principale 6) peut-elle vaincre la Liche ?

Chemin le plus court : entrée -> hall -> couloir (Rat géant) -> antichambre (Ogre)
-> repos -> salle du trône (La Liche). Le voleur est simulé SANS aucun critique
(pire cas) : les critiques ne peuvent qu'améliorer le résultat.

Lancer depuis la racine du projet :
    python -m scripts.simulation
"""

from app.domain.combat import EN_COURS, HEROS_MORT, jouer_tour
from app.domain.heros import Guerrier, Heros, Mage, Voleur
from app.services.dungeon_map import get_monster

PARCOURS = [["rat_geant", "ogre"], ["liche"]]  # un repos entre les deux groupes

HEROS_TESTES: dict[str, Heros] = {
    "guerrier": Guerrier(force=6, agilite=2, intelligence=2),
    "mage": Mage(force=2, agilite=2, intelligence=6),
    "voleur": Voleur(force=2, agilite=6, intelligence=2, alea=lambda: 0.99),  # jamais de critique
}


def simuler(heros: Heros) -> tuple[bool, int, list[str]]:
    """Joue le parcours ; renvoie (victoire, PV restants, journal)."""
    pv = heros.pv_max
    journal: list[str] = []
    for numero, groupe in enumerate(PARCOURS):
        if numero > 0:  # repos entre deux groupes de monstres
            pv = heros.pv_max
            journal.append(f"  -- repos : {pv} PV --")
        for monstre_id in groupe:
            monstre = get_monster(monstre_id)
            pv_monstre = monstre["hp"]
            issue = EN_COURS
            while issue == EN_COURS:
                tour = jouer_tour(heros, pv, pv_monstre, monstre["attack"])
                pv, pv_monstre, issue = tour.pv_heros, tour.pv_monstre, tour.issue
                journal.append(
                    f"  {monstre['name']:<10} inflige {tour.degats_infliges:>2}, subit {tour.degats_subis}"
                    f" -> héros {pv:>2} PV, monstre {pv_monstre:>2} PV"
                )
            if issue == HEROS_MORT:
                return False, 0, journal
    return True, pv, journal


def main() -> None:
    for classe, heros in HEROS_TESTES.items():
        victoire, pv, journal = simuler(heros)
        print(f"{classe} (PV max {heros.pv_max}) : {'VICTOIRE' if victoire else 'DÉFAITE'}, {pv} PV restants")
        print("\n".join(journal))


if __name__ == "__main__":
    main()
