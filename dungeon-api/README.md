# Dungeon as a Service

API FastAPI d'un petit jeu de rôle textuel : on crée un compte, on crée un héros,
on explore le donjon salle par salle, on combat des monstres et on tente de vaincre la Liche.

## Installation (à faire une seule fois)

Prérequis : Python 3.10 ou plus récent (`python --version`).

```bash
# 1. Créer et activer un environnement virtuel
python -m venv .venv
# Windows (PowerShell) :
.venv\Scripts\Activate.ps1
# macOS / Linux :
source .venv/bin/activate

# 2. Installer les dépendances
pip install -r requirements.txt
```

## Lancer l'API

Depuis la racine du projet (le dossier qui contient `app/`) :

```bash
fastapi dev app/main.py
```

Puis http://127.0.0.1:8000/docs. Pour tester les routes protégées dans Swagger :
`POST /auth/register`, puis le bouton **Authorize** (username + password), et c'est parti.

Variables d'environnement (toutes optionnelles) :

| Variable | Défaut | Rôle |
|---|---|---|
| `JWT_SECRET_KEY` | valeur de dev | secret de signature des JWT, **à changer en production** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | durée de vie d'un token |
| `DATABASE_URL` | `sqlite:///./dungeon.db` | base de données (PostgreSQL possible, voir plus bas) |

## Les routes

| Méthode | Route | Auth | Rôle |
|---|---|---|---|
| GET | `/health` | non | le serveur répond |
| POST | `/auth/register` | non | crée un joueur (201) |
| POST | `/auth/login` | non | formulaire OAuth2, renvoie `{"access_token", "token_type": "bearer"}` |
| POST | `/heroes` | oui | crée un héros (201) |
| GET | `/heroes` | oui | liste **mes** héros |
| GET | `/heroes/{id}` | oui | détail d'un héros (même mort) |
| GET | `/heroes/{id}/room` | oui | salle actuelle (+ monstre si combat) |
| POST | `/heroes/{id}/move` | oui | `{"direction": "nord"\|"sud"\|"est"\|"ouest"}` |
| POST | `/heroes/{id}/attack` | oui | un tour de combat |
| POST | `/heroes/{id}/rest` | oui | repos de 3 s, PV au max |
| GET | `/leaderboard` | non | top 10 (victoires puis or) |

Toutes les erreurs métier ont la même forme :

```json
{"detail": {"error": "NO_EXIT", "message": "Il n'y a pas de passage vers le est."}}
```

| Code HTTP | `error` | Quand |
|---|---|---|
| 400 | `NO_EXIT` | pas de sortie dans cette direction |
| 401 | `NOT_AUTHENTICATED`, `INVALID_TOKEN` | token absent, invalide ou expiré |
| 401 | `INVALID_CREDENTIALS` | mauvais identifiants au login |
| 403 | `NOT_YOUR_HERO` | le héros appartient à un autre joueur |
| 404 | `HERO_NOT_FOUND` | id de héros inconnu (testé **avant** le 403) |
| 409 | `USERNAME_TAKEN` | nom d'utilisateur déjà pris |
| 409 | `HERO_DEAD` | le héros est mort (testé en premier sur move/attack/rest) |
| 409 | `IN_COMBAT` | move ou rest pendant un combat |
| 409 | `NO_MONSTER` | attack sans monstre |

Les 422 sont ceux de FastAPI/Pydantic (body invalide).

## Architecture

```
app/
  main.py              point d'entrée, logging, branchement des routers
  database.py          connexion SQLite/PostgreSQL (FOURNI)
  errors.py            fabrique des HTTPException au format imposé
  models/              tables SQLModel : Player, Hero
  schemas/             entrées/sorties Pydantic (HeroCreate, HeroRead, RoomRead, AttackResult...)
  domain/              règles du jeu en POO, sans FastAPI ni base
    heros.py           Heros (ABC), Guerrier, Mage, Voleur + fabrique CLASSES_HEROS
    combat.py          jouer_tour() : le héros frappe, le monstre riposte s'il survit
  services/            logique applicative (auth, héros, classement)
    dungeon_map.py     lecture de la carte (FOURNI)
  routes/              couche HTTP uniquement (chemins, codes, dépendances)
scripts/               simulation d'équilibrage, export OpenAPI
tests/                 tests pytest
```

Quelques choix :

- **Les routes ne contiennent aucune logique** : elles appellent un service et renvoient son résultat.
  Chaque route a un `response_model`, un tag et des `responses=` qui documentent ses erreurs.
- **Validation 100 % Pydantic** dans `HeroCreate` : nom 3 à 20 caractères, classe par `Enum`,
  stats entières *strictes* entre 1 et 8 (`"6"` et `6.0` sont refusés), somme exactement 10
  (`model_validator`).
- **Aucun `if` sur la classe** dans les services : `creer_heros()` choisit la sous-classe
  via le dictionnaire `CLASSES_HEROS`, puis le service appelle `calculer_degats()` /
  `subir_degats()` (polymorphisme).
- **Voleur** : le tirage aléatoire est une fonction injectée (`alea`), ce qui rend les tests déterministes.
- **`HeroRead`** n'expose ni `monstre_pv` ni `owner_id`, mais `en_combat` et `est_vivant`.
- **Repos** : la route est `async def` et fait `await asyncio.sleep(3)`, donc le serveur continue à
  répondre aux autres requêtes. La transaction de lecture est fermée (`commit`) avant l'attente,
  et le héros est relu (et revérifié) après.
- **Mort du héros** : à 0 PV le combat s'arrête (`monstre_pv` repasse à `None`). Le héros reste
  consultable mais toute action renvoie 409 `HERO_DEAD`.
- **Logging** (bonus B-5) : déplacements, début de combat, chaque tour (dégâts, critique, PV restants),
  repos et victoire sont journalisés via le module `logging` (loggers `dungeon.*`).

## Équilibrage : chaque classe peut battre la Liche

Le script `python -m scripts.simulation` joue le chemin le plus court
(entrée → hall → couloir/Rat → antichambre/Ogre → **repos** → salle du trône/Liche)
avec la stat principale à 6 et les deux autres à 2. Le voleur est simulé **sans aucun critique**
(pire cas). Le même scénario est rejoué par les tests (`test_equilibrage_*` et `test_partie_complete_victoire`).

| Classe | PV max | Dégâts/coup | Subit (Liche, attaque 7) | Liche (50 PV) en | PV restants |
|---|---|---|---|---|---|
| Guerrier (force 6) | 32 | 14 | 6 | 4 coups | 14 |
| Mage (intelligence 6) | 24 | 19 | 7 | 3 coups | 10 |
| Voleur (agilité 6, sans critique) | 24 | 14 | 7 | 4 coups | 3 |

Sans le repos, le voleur arrive face à la Liche avec 12 PV seulement et meurt : le repos est
indispensable pour lui, utile pour les autres. Les critiques du voleur ne peuvent qu'améliorer son résultat.

## Tests

```bash
pytest -v
```

Les tests utilisent une base SQLite en mémoire (override de `get_session`) et remplacent
`asyncio.sleep` pour que le repos ne dure pas 3 s. Ils couvrent les cas nominaux et
les erreurs 401, 403, 404, 400, 409 et 422, plus une partie complète jusqu'à la victoire pour chaque classe.

## Client terminal (bonus)

Le jeu en terminal est dans un dossier séparé : `../dungeon-game/` (voir son README).
Il dialogue avec cette API par HTTP uniquement.

## PostgreSQL avec Docker (bonus)

```bash
docker compose up --build          # base PostgreSQL + API sur http://127.0.0.1:8000
```

Ou seulement la base, avec l'API lancée en local :

```bash
docker compose up -d db
# PowerShell :
$env:DATABASE_URL = "postgresql+psycopg://dungeon:dungeon@localhost:5432/dungeon"
# bash :
export DATABASE_URL=postgresql+psycopg://dungeon:dungeon@localhost:5432/dungeon
fastapi dev app/main.py
```

## Documentation OpenAPI

Le fichier `openapi.json` à la racine est généré sans serveur :

```bash
python -m scripts.export_openapi
```

## Réinitialiser la partie

Arrêtez le serveur et supprimez le fichier `dungeon.db` : il sera recréé au prochain lancement.
À faire aussi si vous ajoutez une colonne à une table (SQLite ne met pas à jour une table existante).

## Travail en groupe : commits réguliers

Chaque membre committe avec son propre compte, souvent et par petites étapes, pour que
l'historique montre qui a fait quoi. Exemple de découpage :

- `feat(palier1): schéma HeroCreate et POST /heroes`
- `feat(palier2): déplacements et salles hantées`
- `feat(palier3): classes Heros/Guerrier/Mage/Voleur et combat`
- `feat(palier4): auth JWT et propriété des héros`
- `test: scénarios d'erreur 401/403/404/409`
- `docs: README et openapi.json`

Lancez `pytest` avant chaque commit et ne committez jamais `dungeon.db`, `.token` ni `.env`
(déjà dans `.gitignore`).

---

<!-- À COMPLÉTER PAR LE GROUPE AVANT LE RENDU -->

## Notre rendu

- **Membres du groupe :** _(à compléter)_
- **Lien du dépôt Git :** _(à compléter)_
- **Palier atteint :** 4 (authentification JWT, propriété des héros, 401/403/409 au format imposé)
- **Bonus réalisés :**
  - B-1 client terminal `../dungeon-game/play.py` (argparse + requests, token dans `.token`) : register, login,
    create, heroes, look, move, attack, rest, health, leaderboard
  - B-2 `GET /leaderboard` public : top 10, victoires d'abord puis or décroissant
  - B-3 tests pytest + TestClient (`tests/`), base en mémoire, `asyncio.sleep` patché
  - B-4 `docker-compose.yml` PostgreSQL (+ `Dockerfile` de l'API), driver `psycopg[binary]`
  - B-5 logging des déplacements et des tours de combat
  - En plus : simulation d'équilibrage (`scripts/simulation.py`), export `openapi.json`
- **Ce qui a été vérifié (Windows 11, Python 3.13, SQLite) :**
  - `pytest` : 38 tests verts (domaine + API).
  - `python -m scripts.simulation` : les trois classes battent la Liche avec un repos
    (PV restants 14 / 10 / 3, cf. tableau plus haut) ; sans repos, le voleur meurt.
  - Scénario complet des paliers 1 à 4 joué contre un vrai serveur uvicorn (base SQLite temporaire) :
    201/422/404, salles et NO_EXIT, combat (réponse exacte du sujet), IN_COMBAT, NO_MONSTER, HERO_DEAD,
    victoire des trois classes, 401/403/404 et isolation des joueurs, classement.
  - Repos : la requête dure ~3 s et `GET /health` répond en quelques millisecondes pendant ce temps.
  - Client `dungeon-game/play.py` : toutes les sous-commandes jouées contre le serveur.
- **Ce qui ne fonctionne pas / limites :**
  - Bonus Docker/PostgreSQL vérifié : `docker compose up -d db`, API lancée avec `DATABASE_URL=postgresql+psycopg://...`,
    inscription, création de héros et déplacement joués, ligne bien présente dans la table `hero` de PostgreSQL.
    L'image `api` du `docker-compose.yml` (Dockerfile) n'a pas été construite.
  - SQLite ne migre pas les tables existantes : supprimer `dungeon.db` après un changement de modèle.
  - Pendant le repos, les accès à la base restent synchrones (SQLModel) : ils sont très courts,
    mais ils s'exécutent sur la boucle d'événements. L'attente de 3 s, elle, ne bloque rien.
  - _(à compléter par le groupe : difficultés rencontrées, ce qui a été vérifié sur vos machines)_
