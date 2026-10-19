"""Classement public des héros."""

from sqlmodel import Session, col, select

from app.models.hero import Hero
from app.models.player import Player
from app.schemas.common import LeaderboardEntry

TAILLE_CLASSEMENT = 10


def get_leaderboard(session: Session) -> list[LeaderboardEntry]:
    """Top 10 : les victorieux d'abord, puis par or décroissant (à égalité, le plus ancien)."""
    lignes = session.exec(
        select(Hero, Player)
        .join(Player, Hero.owner_id == Player.id)
        .order_by(col(Hero.victoire).desc(), col(Hero.or_).desc(), col(Hero.id))
        .limit(TAILLE_CLASSEMENT)
    ).all()
    return [
        LeaderboardEntry(
            rang=rang,
            nom=hero.nom,
            classe=hero.classe,
            joueur=player.username,
            or_=hero.or_,
            victoire=hero.victoire,
        )
        for rang, (hero, player) in enumerate(lignes, start=1)
    ]
