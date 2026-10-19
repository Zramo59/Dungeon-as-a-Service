"""Logique du jeu : création, déplacement, combat et repos des héros."""

import asyncio
import logging

from fastapi import status
from sqlmodel import Session, select

from app.domain.combat import HEROS_MORT, MONSTRE_VAINCU, jouer_tour
from app.domain.heros import Heros, creer_heros
from app.errors import api_error
from app.models.hero import Hero
from app.models.player import Player
from app.schemas.hero import AttackResult, Direction, HeroCreate, HeroRead, MonsterRead, RoomRead
from app.services.dungeon_map import FINAL_ROOM, START_ROOM, get_monster_of_room, get_room

logger = logging.getLogger("dungeon.jeu")

DUREE_REPOS_SECONDES = 3


# --- Conversions -------------------------------------------------------------


def to_read(hero: Hero) -> HeroRead:
    """Convertit la table en schéma de sortie (masque monstre_pv et owner_id)."""
    return HeroRead(
        id=hero.id,
        nom=hero.nom,
        classe=hero.classe,
        force=hero.force,
        agilite=hero.agilite,
        intelligence=hero.intelligence,
        pv=hero.pv,
        pv_max=hero.pv_max,
        salle_actuelle=hero.salle_actuelle,
        or_=hero.or_,
        victoire=hero.victoire,
        en_combat=hero.monstre_pv is not None,
        est_vivant=hero.pv > 0,
    )


def construire_heros(hero: Hero) -> Heros:
    """Construit l'objet métier (Guerrier, Mage ou Voleur) à partir de la table."""
    return creer_heros(hero.classe, hero.force, hero.agilite, hero.intelligence)


# --- Accès et vérifications ----------------------------------------------------


def get_owned_hero(session: Session, hero_id: int, player: Player) -> Hero:
    """Renvoie le héros s'il appartient au joueur : 404 s'il n'existe pas, puis 403."""
    hero = session.get(Hero, hero_id)
    if hero is None:
        raise api_error(status.HTTP_404_NOT_FOUND, "HERO_NOT_FOUND", f"Aucun héros avec l'id {hero_id}.")
    if hero.owner_id != player.id:
        raise api_error(status.HTTP_403_FORBIDDEN, "NOT_YOUR_HERO", "Ce héros appartient à un autre joueur.")
    return hero


def ensure_alive(hero: Hero) -> None:
    """409 HERO_DEAD si le héros n'a plus de PV."""
    if hero.pv <= 0:
        raise api_error(status.HTTP_409_CONFLICT, "HERO_DEAD", f"{hero.nom} est mort : il ne peut plus agir.")


def ensure_not_in_combat(hero: Hero) -> None:
    """409 IN_COMBAT si un monstre bloque le héros."""
    if hero.monstre_pv is not None:
        raise api_error(status.HTTP_409_CONFLICT, "IN_COMBAT", f"{hero.nom} est en plein combat : battez-vous d'abord !")


# --- Cas d'usage --------------------------------------------------------------


def create_hero(session: Session, data: HeroCreate, player: Player) -> HeroRead:
    """Crée un héros dans la salle de départ, PV au maximum."""
    pv_max = creer_heros(data.classe.value, data.force, data.agilite, data.intelligence).pv_max
    hero = Hero(
        nom=data.nom,
        classe=data.classe.value,
        force=data.force,
        agilite=data.agilite,
        intelligence=data.intelligence,
        pv=pv_max,
        pv_max=pv_max,
        salle_actuelle=START_ROOM,
        owner_id=player.id,
    )
    session.add(hero)
    session.commit()
    session.refresh(hero)
    logger.info("Héros créé : %s (#%s, %s) pour le joueur #%s", hero.nom, hero.id, hero.classe, player.id)
    return to_read(hero)


def list_heroes(session: Session, player: Player) -> list[HeroRead]:
    """Héros du joueur connecté uniquement."""
    heroes = session.exec(select(Hero).where(Hero.owner_id == player.id).order_by(Hero.id)).all()
    return [to_read(h) for h in heroes]


def get_hero(session: Session, hero_id: int, player: Player) -> HeroRead:
    """Détail d'un héros (consultable même mort)."""
    return to_read(get_owned_hero(session, hero_id, player))


def describe_room(hero: Hero) -> RoomRead:
    """Salle actuelle du héros, avec le monstre s'il y a un combat en cours."""
    room = get_room(hero.salle_actuelle)
    monstre = None
    if hero.monstre_pv is not None:
        modele = get_monster_of_room(hero.salle_actuelle)
        monstre = MonsterRead(
            id=room["monster"],
            nom=modele["name"],
            pv=hero.monstre_pv,
            pv_max=modele["hp"],
            attaque=modele["attack"],
        )
    return RoomRead(
        id=hero.salle_actuelle,
        nom=room["name"],
        description=room["description"],
        sorties=room["exits"],
        monstre=monstre,
    )


def get_hero_room(session: Session, hero_id: int, player: Player) -> RoomRead:
    """GET /heroes/{id}/room."""
    return describe_room(get_owned_hero(session, hero_id, player))


def move_hero(session: Session, hero_id: int, player: Player, direction: Direction) -> RoomRead:
    """Déplace le héros ; entrer dans une salle hantée (re)déclenche un combat."""
    hero = get_owned_hero(session, hero_id, player)
    ensure_alive(hero)
    ensure_not_in_combat(hero)

    sorties = get_room(hero.salle_actuelle)["exits"]
    destination = sorties.get(direction.value)
    if destination is None:
        raise api_error(status.HTTP_400_BAD_REQUEST, "NO_EXIT", f"Il n'y a pas de passage vers le {direction.value}.")

    depart = hero.salle_actuelle
    hero.salle_actuelle = destination
    monstre = get_monster_of_room(destination)
    # Le monstre réapparaît à chaque entrée avec tous ses PV
    hero.monstre_pv = monstre["hp"] if monstre else None
    session.add(hero)
    session.commit()
    session.refresh(hero)

    logger.info("Déplacement : %s (#%s) %s -> %s (%s)", hero.nom, hero.id, depart, destination, direction.value)
    if monstre:
        logger.info("Combat : %s (#%s) affronte %s (%s PV)", hero.nom, hero.id, monstre["name"], monstre["hp"])
    return describe_room(hero)


def attack(session: Session, hero_id: int, player: Player) -> AttackResult:
    """Joue un tour de combat : le héros frappe, puis le monstre riposte s'il survit."""
    hero = get_owned_hero(session, hero_id, player)
    ensure_alive(hero)
    if hero.monstre_pv is None:
        raise api_error(status.HTTP_409_CONFLICT, "NO_MONSTER", "Il n'y a aucun monstre à attaquer ici.")

    monstre = get_monster_of_room(hero.salle_actuelle)
    tour = jouer_tour(construire_heros(hero), hero.pv, hero.monstre_pv, monstre["attack"])

    hero.pv = tour.pv_heros
    or_gagne = 0
    boss_vaincu = False
    if tour.issue == MONSTRE_VAINCU:
        or_gagne = monstre["gold"]
        hero.or_ += or_gagne
        hero.monstre_pv = None
        boss_vaincu = hero.salle_actuelle == FINAL_ROOM
        if boss_vaincu:
            hero.victoire = True
    elif tour.issue == HEROS_MORT:
        hero.monstre_pv = None  # le combat s'arrête avec la mort du héros
    else:
        hero.monstre_pv = tour.pv_monstre
    session.add(hero)
    session.commit()
    session.refresh(hero)

    logger.info(
        "Tour de combat : %s (#%s) inflige %s%s à %s (reste %s PV), subit %s (reste %s PV) -> %s",
        hero.nom, hero.id, tour.degats_infliges, " (critique)" if tour.critique else "",
        monstre["name"], tour.pv_monstre, tour.degats_subis, tour.pv_heros, tour.issue,
    )
    if boss_vaincu:
        logger.info("VICTOIRE : %s (#%s) a vaincu %s !", hero.nom, hero.id, monstre["name"])

    return AttackResult(
        degats_infliges=tour.degats_infliges,
        critique=tour.critique,
        degats_subis=tour.degats_subis,
        pv_heros=tour.pv_heros,
        pv_monstre=tour.pv_monstre,
        issue=tour.issue,
        or_gagne=or_gagne,
        victoire=hero.victoire,
    )


async def rest(session: Session, hero_id: int, player: Player) -> HeroRead:
    """Repos de 3 s puis PV au maximum, sans bloquer la boucle d'événements.

    La transaction de lecture est close avant l'attente : aucune connexion
    n'est monopolisée pendant le sommeil.
    """
    hero = get_owned_hero(session, hero_id, player)
    ensure_alive(hero)
    ensure_not_in_combat(hero)
    logger.info("Repos : %s (#%s) se repose %s s", hero.nom, hero_id, DUREE_REPOS_SECONDES)
    # Termine la transaction de lecture avant l'attente (on ne touche plus aux
    # objets avant la fin du sommeil pour ne pas en rouvrir une)
    session.commit()

    await asyncio.sleep(DUREE_REPOS_SECONDES)

    # On relit le héros : son état a pu changer pendant le repos
    hero = get_owned_hero(session, hero_id, player)
    ensure_alive(hero)
    ensure_not_in_combat(hero)
    hero.pv = hero.pv_max
    session.add(hero)
    session.commit()
    session.refresh(hero)
    logger.info("Repos terminé : %s (#%s) a %s/%s PV", hero.nom, hero.id, hero.pv, hero.pv_max)
    return to_read(hero)
