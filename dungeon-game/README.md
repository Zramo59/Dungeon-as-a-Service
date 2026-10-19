# Dungeon as a Service — client de jeu (terminal)

Le jeu en ligne de commande. Il ne contient aucune règle : tout le moteur est dans l'API (`../dungeon-api/`),
ce client envoie seulement des requêtes HTTP.

## Utilisation

1. Lancer l'API (dans `../dungeon-api/`) : `fastapi dev app/main.py`
2. Ici :

```bash
pip install -r requirements.txt
python play.py health
python play.py register --username alice --password secret
python play.py login --username alice --password secret      # token stocké dans .token
python play.py create --name Aragorn --classe guerrier --force 6 --agilite 2 --intelligence 2
python play.py look --hero 1
python play.py move --hero 1 --direction nord
python play.py attack --hero 1
python play.py rest --hero 1
python play.py heroes
python play.py leaderboard
```

L'URL de l'API se change avec la variable d'environnement `DUNGEON_API_URL` (défaut `http://127.0.0.1:8000`).
