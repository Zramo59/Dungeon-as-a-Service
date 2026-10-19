"""Routes des héros : uniquement la couche HTTP, la logique est dans hero_service."""

from fastapi import APIRouter, status

from app.routes.dependencies import CurrentPlayer, SessionDep
from app.schemas.common import error_doc
from app.schemas.hero import AttackResult, HeroCreate, HeroRead, MoveRequest, RoomRead
from app.services import hero_service

ERR_403 = {403: error_doc("NOT_YOUR_HERO : le héros appartient à un autre joueur")}
ERR_404 = {404: error_doc("HERO_NOT_FOUND : héros inconnu")}
ERR_HERO = {**ERR_404, **ERR_403}

router = APIRouter(
    prefix="/heroes",
    tags=["Héros"],
    responses={401: error_doc("NOT_AUTHENTICATED / INVALID_TOKEN : token absent ou invalide")},
)


@router.post("", response_model=HeroRead, status_code=status.HTTP_201_CREATED)
def create_hero(data: HeroCreate, session: SessionDep, player: CurrentPlayer) -> HeroRead:
    """Crée un héros (validation 100 % Pydantic : 422 si invalide)."""
    return hero_service.create_hero(session, data, player)


@router.get("", response_model=list[HeroRead])
def list_heroes(session: SessionDep, player: CurrentPlayer) -> list[HeroRead]:
    """Liste les héros du joueur connecté."""
    return hero_service.list_heroes(session, player)


@router.get("/{hero_id}", response_model=HeroRead, responses=ERR_HERO)
def get_hero(hero_id: int, session: SessionDep, player: CurrentPlayer) -> HeroRead:
    """Détail d'un héros (même mort)."""
    return hero_service.get_hero(session, hero_id, player)


@router.get("/{hero_id}/room", response_model=RoomRead, responses=ERR_HERO)
def get_room(hero_id: int, session: SessionDep, player: CurrentPlayer) -> RoomRead:
    """Salle actuelle du héros (avec le monstre si un combat est en cours)."""
    return hero_service.get_hero_room(session, hero_id, player)


@router.post(
    "/{hero_id}/move",
    response_model=RoomRead,
    responses={
        **ERR_HERO,
        400: error_doc("NO_EXIT : pas de passage dans cette direction"),
        409: error_doc("HERO_DEAD ou IN_COMBAT"),
    },
)
def move(hero_id: int, data: MoveRequest, session: SessionDep, player: CurrentPlayer) -> RoomRead:
    """Déplace le héros et renvoie la nouvelle salle."""
    return hero_service.move_hero(session, hero_id, player, data.direction)


@router.post(
    "/{hero_id}/attack",
    response_model=AttackResult,
    responses={**ERR_HERO, 409: error_doc("HERO_DEAD ou NO_MONSTER")},
)
def attack(hero_id: int, session: SessionDep, player: CurrentPlayer) -> AttackResult:
    """Joue un tour de combat contre le monstre de la salle."""
    return hero_service.attack(session, hero_id, player)


@router.post(
    "/{hero_id}/rest",
    response_model=HeroRead,
    responses={**ERR_HERO, 409: error_doc("HERO_DEAD ou IN_COMBAT")},
)
async def rest(hero_id: int, session: SessionDep, player: CurrentPlayer) -> HeroRead:
    """Repos de 3 secondes (non bloquant pour le serveur) puis PV au maximum."""
    return await hero_service.rest(session, hero_id, player)
