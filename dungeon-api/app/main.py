"""Point d'entrée de l'API Dungeon as a Service.

Lancer le serveur depuis la racine du projet :
    fastapi dev app/main.py
Puis ouvrir http://127.0.0.1:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import create_db_and_tables

# Les modèles doivent être importés AVANT create_db_and_tables pour que SQLModel les connaisse
from app.models.hero import Hero  # noqa: F401
from app.models.player import Player  # noqa: F401
from app.routes import auth, heroes, public

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Exécuté une fois au démarrage du serveur : crée les tables si besoin
    create_db_and_tables()
    yield


app = FastAPI(
    title="Dungeon as a Service",
    description="Moteur de jeu de rôle textuel — Pixel Crypt",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(public.router)
app.include_router(auth.router)
app.include_router(heroes.router)
