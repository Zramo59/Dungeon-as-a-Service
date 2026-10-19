"""Fixtures pytest : base SQLite en mémoire isolée pour chaque test."""

import asyncio
from collections.abc import Callable, Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.database import get_session
from app.main import app


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """TestClient branché sur une base temporaire (override de get_session)."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)

    def get_session_override() -> Generator[Session, None, None]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_session] = get_session_override
    # Sans "with" : le lifespan (qui créerait dungeon.db) n'est pas exécuté
    yield TestClient(app)
    app.dependency_overrides.clear()
    engine.dispose()


@pytest.fixture
def sleep_calls(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """Remplace asyncio.sleep : le repos ne dure plus 3 s, on note juste la durée demandée."""
    calls: list[float] = []
    real_sleep = asyncio.sleep

    async def fake_sleep(delay: float, *args, **kwargs) -> None:
        calls.append(delay)
        await real_sleep(0)

    monkeypatch.setattr("app.services.hero_service.asyncio.sleep", fake_sleep)
    return calls


@pytest.fixture
def auth(client: TestClient) -> Callable[[str], dict[str, str]]:
    """Inscrit + connecte un joueur et renvoie ses en-têtes Authorization."""

    def _auth(username: str = "alice", password: str = "secret") -> dict[str, str]:
        client.post("/auth/register", json={"username": username, "password": password})
        r = client.post("/auth/login", data={"username": username, "password": password})
        assert r.status_code == 200, r.text
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _auth


@pytest.fixture
def make_hero(client: TestClient) -> Callable[..., dict]:
    """Crée un héros pour un joueur donné et renvoie le JSON."""

    def _make(headers: dict[str, str], classe: str = "guerrier", **changes: object) -> dict:
        body = {"nom": "Aragorn", "classe": classe, "force": 6, "agilite": 2, "intelligence": 2}
        body.update(changes)
        r = client.post("/heroes", json=body, headers=headers)
        assert r.status_code == 201, r.text
        return r.json()

    return _make
