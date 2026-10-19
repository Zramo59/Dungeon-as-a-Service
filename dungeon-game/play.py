"""BONUS — Client terminal du jeu (argparse + requests).

Exemples (depuis ce dossier, API lancée) :
    python play.py register --username alice --password secret
    python play.py login --username alice --password secret
    python play.py create --name Aragorn --classe guerrier --force 6 --agilite 2 --intelligence 2
    python play.py heroes
    python play.py look --hero 1
    python play.py move --hero 1 --direction nord
    python play.py attack --hero 1
    python play.py rest --hero 1
    python play.py leaderboard

Le token JWT reçu au login est enregistré dans le fichier .token (ignoré par Git).
L'URL de l'API peut être changée avec la variable d'environnement DUNGEON_API_URL.
"""

import argparse
import os
import sys
from pathlib import Path

import requests

API_URL = os.getenv("DUNGEON_API_URL", "http://127.0.0.1:8000")
TOKEN_FILE = Path(".token")
TIMEOUT = 10


def load_headers() -> dict[str, str]:
    """En-têtes Authorization à partir du token enregistré."""
    if not TOKEN_FILE.exists():
        sys.exit("Pas de token : connectez-vous d'abord avec la commande login.")
    return {"Authorization": f"Bearer {TOKEN_FILE.read_text(encoding='utf-8').strip()}"}


def check(response: requests.Response) -> dict | list:
    """Affiche l'erreur de l'API et quitte si la requête a échoué."""
    if response.ok:
        return response.json()
    try:
        detail = response.json().get("detail")
    except ValueError:
        detail = response.text
    if isinstance(detail, dict):
        sys.exit(f"Erreur {response.status_code} [{detail.get('error')}] : {detail.get('message')}")
    sys.exit(f"Erreur {response.status_code} : {detail}")


def show_hero(h: dict) -> None:
    etat = "mort" if not h["est_vivant"] else ("en combat" if h["en_combat"] else "libre")
    print(
        f"#{h['id']} {h['nom']} ({h['classe']}) — PV {h['pv']}/{h['pv_max']} — or {h['or_']}"
        f" — salle {h['salle_actuelle']} — {etat}{' — VICTOIRE !' if h['victoire'] else ''}"
    )


def show_room(r: dict) -> None:
    print(f"== {r['nom']} ==\n{r['description']}")
    print("Sorties : " + ", ".join(f"{d} -> {s}" for d, s in r["sorties"].items()))
    if r["monstre"]:
        m = r["monstre"]
        print(f"!! {m['nom']} vous attaque : {m['pv']}/{m['pv_max']} PV, attaque {m['attaque']}")


def show_attack(a: dict) -> None:
    crit = " (CRITIQUE !)" if a["critique"] else ""
    print(f"Vous infligez {a['degats_infliges']} dégâts{crit}. Le monstre a encore {a['pv_monstre']} PV.")
    if a["degats_subis"]:
        print(f"Il riposte : vous perdez {a['degats_subis']} PV ({a['pv_heros']} restants).")
    messages = {
        "monstre_vaincu": f"Monstre vaincu ! +{a['or_gagne']} pièces d'or.",
        "heros_mort": "Votre héros est mort...",
        "en_cours": "Le combat continue.",
    }
    print(messages[a["issue"]])
    if a["victoire"]:
        print("*** VICTOIRE : la Liche est vaincue ! ***")


def main() -> None:
    parser = argparse.ArgumentParser(description="Dungeon as a Service — client terminal")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health", help="Vérifie que l'API répond")
    for name in ("register", "login"):
        p = sub.add_parser(name, help="Crée un compte" if name == "register" else "Se connecte")
        p.add_argument("--username", required=True)
        p.add_argument("--password", required=True)
    p = sub.add_parser("create", help="Crée un héros")
    p.add_argument("--name", required=True)
    p.add_argument("--classe", required=True, choices=["guerrier", "mage", "voleur"])
    for stat in ("force", "agilite", "intelligence"):
        p.add_argument(f"--{stat}", type=int, required=True)
    sub.add_parser("heroes", help="Liste vos héros")
    for name, aide in (("look", "Décrit la salle"), ("attack", "Attaque le monstre"), ("rest", "Se repose (3 s)")):
        sub.add_parser(name, help=aide).add_argument("--hero", type=int, required=True)
    p = sub.add_parser("move", help="Se déplace")
    p.add_argument("--hero", type=int, required=True)
    p.add_argument("--direction", required=True, choices=["nord", "sud", "est", "ouest"])
    sub.add_parser("leaderboard", help="Affiche le classement")

    args = parser.parse_args()

    try:
        if args.command == "health":
            print(check(requests.get(f"{API_URL}/health", timeout=TIMEOUT))["message"])
        elif args.command == "register":
            data = check(requests.post(
                f"{API_URL}/auth/register",
                json={"username": args.username, "password": args.password},
                timeout=TIMEOUT,
            ))
            print(f"Compte créé : {data['username']} (#{data['id']})")
        elif args.command == "login":
            data = check(requests.post(
                f"{API_URL}/auth/login",
                data={"username": args.username, "password": args.password},
                timeout=TIMEOUT,
            ))
            TOKEN_FILE.write_text(data["access_token"], encoding="utf-8")
            print(f"Connecté ! Token enregistré dans {TOKEN_FILE}.")
        elif args.command == "create":
            body = {"nom": args.name, "classe": args.classe, "force": args.force,
                    "agilite": args.agilite, "intelligence": args.intelligence}
            show_hero(check(requests.post(f"{API_URL}/heroes", json=body, headers=load_headers(), timeout=TIMEOUT)))
        elif args.command == "heroes":
            for h in check(requests.get(f"{API_URL}/heroes", headers=load_headers(), timeout=TIMEOUT)):
                show_hero(h)
        elif args.command == "look":
            headers = load_headers()
            show_hero(check(requests.get(f"{API_URL}/heroes/{args.hero}", headers=headers, timeout=TIMEOUT)))
            show_room(check(requests.get(f"{API_URL}/heroes/{args.hero}/room", headers=headers, timeout=TIMEOUT)))
        elif args.command == "move":
            show_room(check(requests.post(
                f"{API_URL}/heroes/{args.hero}/move",
                json={"direction": args.direction},
                headers=load_headers(),
                timeout=TIMEOUT,
            )))
        elif args.command == "attack":
            show_attack(check(requests.post(f"{API_URL}/heroes/{args.hero}/attack", headers=load_headers(), timeout=TIMEOUT)))
        elif args.command == "rest":
            print("Vous vous reposez...")
            show_hero(check(requests.post(f"{API_URL}/heroes/{args.hero}/rest", headers=load_headers(), timeout=TIMEOUT)))
        elif args.command == "leaderboard":
            for e in check(requests.get(f"{API_URL}/leaderboard", timeout=TIMEOUT)):
                print(f"{e['rang']:>2}. {e['nom']} ({e['classe']}, {e['joueur']}) — {e['or_']} or"
                      f"{' — VICTOIRE' if e['victoire'] else ''}")
    except requests.ConnectionError:
        sys.exit(f"Impossible de joindre l'API sur {API_URL} : le serveur est-il lancé ?")


if __name__ == "__main__":
    main()
