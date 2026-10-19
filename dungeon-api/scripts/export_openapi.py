"""Exporte le schéma OpenAPI dans openapi.json (sans lancer de serveur).

Lancer depuis la racine du projet :
    python -m scripts.export_openapi
"""

import json
from pathlib import Path

from app.main import app

API_DIR = Path(__file__).resolve().parents[1]
# Une copie dans le dossier de l'API et une à la racine du dépôt (si elle existe)
SORTIES = [API_DIR / "openapi.json", API_DIR.parent / "openapi.json"]


def main() -> None:
    contenu = json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n"
    for sortie in SORTIES:
        if sortie.parent == API_DIR or (sortie.parent / "dungeon-api").is_dir():
            sortie.write_text(contenu, encoding="utf-8")
            print(f"Schéma écrit dans {sortie}")


if __name__ == "__main__":
    main()
