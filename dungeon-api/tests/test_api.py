"""Tests de l'API via TestClient (base SQLite en mémoire, repos accéléré)."""

import pytest
from fastapi.testclient import TestClient


def error_of(response) -> str:
    """Code d'erreur métier (et vérifie le format imposé)."""
    detail = response.json()["detail"]
    assert set(detail) == {"error", "message"}
    return detail["error"]


def go(client: TestClient, hero_id: int, headers: dict, *directions: str):
    """Enchaîne des déplacements et renvoie la dernière réponse."""
    r = None
    for d in directions:
        r = client.post(f"/heroes/{hero_id}/move", json={"direction": d}, headers=headers)
    return r


def fight(client: TestClient, hero_id: int, headers: dict) -> dict:
    """Attaque jusqu'à la fin du combat et renvoie le dernier tour."""
    while True:
        r = client.post(f"/heroes/{hero_id}/attack", headers=headers)
        assert r.status_code == 200, r.text
        if r.json()["issue"] != "en_cours":
            return r.json()


# --- Système et authentification ------------------------------------------------


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


def test_register_et_username_pris(client):
    r = client.post("/auth/register", json={"username": "alice", "password": "secret"})
    assert r.status_code == 201
    assert r.json()["username"] == "alice" and "password" not in r.text
    r = client.post("/auth/register", json={"username": "alice", "password": "autre"})
    assert r.status_code == 409 and error_of(r) == "USERNAME_TAKEN"


def test_login_mauvais_identifiants(client, auth):
    auth("alice", "secret")
    r = client.post("/auth/login", data={"username": "alice", "password": "faux"})
    assert r.status_code == 401 and error_of(r) == "INVALID_CREDENTIALS"
    r = client.post("/auth/login", data={"username": "inconnu", "password": "x"})
    assert r.status_code == 401


def test_login_renvoie_un_token_bearer(client, auth):
    client.post("/auth/register", json={"username": "bob", "password": "secret"})
    r = client.post("/auth/login", data={"username": "bob", "password": "secret"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer" and r.json()["access_token"]


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer pas-un-jwt"}])
def test_heroes_sans_token_valide_401(client, headers):
    r = client.get("/heroes", headers=headers)
    assert r.status_code == 401
    assert error_of(r) in {"NOT_AUTHENTICATED", "INVALID_TOKEN"}


# --- Palier 1 : création et validation ----------------------------------------------


def test_creation_heros(client, auth):
    h = auth()
    r = client.post(
        "/heroes",
        json={"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2},
        headers=h,
    )
    assert r.status_code == 201
    hero = r.json()
    assert hero["salle_actuelle"] == "entree"
    assert hero["pv"] == hero["pv_max"] == 32
    assert hero["or_"] == 0 and hero["victoire"] is False
    assert hero["en_combat"] is False and hero["est_vivant"] is True
    assert "monstre_pv" not in hero and "owner_id" not in hero


@pytest.mark.parametrize(
    "changes",
    [
        {"nom": "Al"},  # trop court
        {"nom": "A" * 21},  # trop long
        {"classe": "paladin"},
        {"force": 0, "agilite": 8},  # stat < 1
        {"force": 9, "agilite": 0},  # stat > 8
        {"force": 5},  # somme = 9
        {"force": 7},  # somme = 11
        {"force": 6.0},  # pas un entier
        {"force": "6"},  # pas un entier
    ],
)
def test_creation_invalide_422(client, auth, changes):
    body = {"nom": "Aragorn", "classe": "guerrier", "force": 6, "agilite": 2, "intelligence": 2}
    body.update(changes)
    r = client.post("/heroes", json=body, headers=auth())
    assert r.status_code == 422


def test_lecture_et_liste(client, auth, make_hero):
    alice, bob = auth("alice"), auth("bob")
    hero = make_hero(alice)
    make_hero(bob)
    assert [x["id"] for x in client.get("/heroes", headers=alice).json()] == [hero["id"]]
    assert client.get(f"/heroes/{hero['id']}", headers=alice).json() == hero


def test_heros_inconnu_404_puis_403(client, auth, make_hero):
    alice, bob = auth("alice"), auth("bob")
    hero = make_hero(alice)
    r = client.get("/heroes/999", headers=bob)
    assert r.status_code == 404 and error_of(r) == "HERO_NOT_FOUND"
    for method, path in [("get", ""), ("get", "/room"), ("post", "/attack"), ("post", "/rest")]:
        r = getattr(client, method)(f"/heroes/{hero['id']}{path}", headers=bob)
        assert r.status_code == 403 and error_of(r) == "NOT_YOUR_HERO"


# --- Palier 2 : salles et déplacements ----------------------------------------------


def test_salle_et_deplacement(client, auth, make_hero):
    h = auth()
    hero = make_hero(h)
    room = client.get(f"/heroes/{hero['id']}/room", headers=h).json()
    assert room["id"] == "entree" and room["sorties"] == {"nord": "hall"} and room["monstre"] is None

    r = go(client, hero["id"], h, "nord")
    assert r.status_code == 200 and r.json()["id"] == "hall"
    assert client.get(f"/heroes/{hero['id']}", headers=h).json()["salle_actuelle"] == "hall"


def test_pas_de_sortie_400(client, auth, make_hero):
    h = auth()
    hero = make_hero(h)
    r = go(client, hero["id"], h, "est")
    assert r.status_code == 400 and error_of(r) == "NO_EXIT"
    assert r.json()["detail"]["message"] == "Il n'y a pas de passage vers le est."


def test_direction_invalide_422(client, auth, make_hero):
    h = auth()
    hero = make_hero(h)
    assert go(client, hero["id"], h, "haut").status_code == 422


def test_salle_hantee_demarre_un_combat(client, auth, make_hero, sleep_calls):
    h = auth()
    hero = make_hero(h)
    room = go(client, hero["id"], h, "nord", "est").json()  # crypte : squelette
    assert room["monstre"]["nom"] == "Squelette" and room["monstre"]["pv"] == 15
    assert client.get(f"/heroes/{hero['id']}", headers=h).json()["en_combat"] is True

    r = go(client, hero["id"], h, "ouest")
    assert r.status_code == 409 and error_of(r) == "IN_COMBAT"
    r = client.post(f"/heroes/{hero['id']}/rest", headers=h)
    assert r.status_code == 409 and error_of(r) == "IN_COMBAT"


# --- Palier 3 : combat et repos -----------------------------------------------------


def test_attaque_sans_monstre_409(client, auth, make_hero):
    h = auth()
    hero = make_hero(h)
    r = client.post(f"/heroes/{hero['id']}/attack", headers=h)
    assert r.status_code == 409 and error_of(r) == "NO_MONSTER"


def test_tour_de_combat_et_reapparition(client, auth, make_hero):
    h = auth()
    hero = make_hero(h)  # guerrier force 6 : 14 dégâts
    go(client, hero["id"], h, "nord", "est")  # squelette 15 PV, attaque 4
    r = client.post(f"/heroes/{hero['id']}/attack", headers=h)
    assert r.json() == {
        "degats_infliges": 14, "critique": False, "degats_subis": 3, "pv_heros": 29,
        "pv_monstre": 1, "issue": "en_cours", "or_gagne": 0, "victoire": False,
    }
    r = client.post(f"/heroes/{hero['id']}/attack", headers=h).json()
    assert r["issue"] == "monstre_vaincu" and r["or_gagne"] == 15 and r["pv_monstre"] == 0
    state = client.get(f"/heroes/{hero['id']}", headers=h).json()
    assert state["or_"] == 15 and state["en_combat"] is False

    # Le monstre réapparaît à chaque entrée
    room = go(client, hero["id"], h, "ouest", "est").json()
    assert room["monstre"]["pv"] == 15


def test_repos(client, auth, make_hero, sleep_calls):
    h = auth()
    hero = make_hero(h)
    go(client, hero["id"], h, "nord", "est")
    fight(client, hero["id"], h)
    r = client.post(f"/heroes/{hero['id']}/rest", headers=h)
    assert r.status_code == 200
    assert r.json()["pv"] == r.json()["pv_max"] == 32
    assert 3 in sleep_calls


def test_heros_mort(client, auth, make_hero, sleep_calls):
    h = auth()
    # Mage très faible : 4 dégâts par coup, 22 PV : l'Ogre finit par le tuer
    hero = make_hero(h, classe="mage", force=1, agilite=8, intelligence=1)
    go(client, hero["id"], h, "nord", "nord")
    assert fight(client, hero["id"], h)["issue"] == "monstre_vaincu"  # rat
    go(client, hero["id"], h, "nord")
    last = fight(client, hero["id"], h)  # ogre
    assert last["issue"] == "heros_mort" and last["pv_heros"] == 0

    state = client.get(f"/heroes/{hero['id']}", headers=h)  # toujours consultable
    assert state.status_code == 200 and state.json()["est_vivant"] is False
    for path, body in [("/move", {"direction": "sud"}), ("/attack", None), ("/rest", None)]:
        r = client.post(f"/heroes/{hero['id']}{path}", json=body, headers=h)
        assert r.status_code == 409 and error_of(r) == "HERO_DEAD"


@pytest.mark.parametrize(
    "classe,stats",
    [
        ("guerrier", {"force": 6, "agilite": 2, "intelligence": 2}),
        ("mage", {"force": 2, "agilite": 2, "intelligence": 6}),
        ("voleur", {"force": 2, "agilite": 6, "intelligence": 2}),
    ],
)
def test_partie_complete_victoire(client, auth, make_hero, sleep_calls, classe, stats):
    """Chaque classe (stat principale 6) bat la Liche avec un repos avant le trône."""
    h = auth()
    hero = make_hero(h, classe=classe, **stats)
    go(client, hero["id"], h, "nord", "nord")
    assert fight(client, hero["id"], h)["issue"] == "monstre_vaincu"  # rat
    go(client, hero["id"], h, "nord")
    assert fight(client, hero["id"], h)["issue"] == "monstre_vaincu"  # ogre
    assert client.post(f"/heroes/{hero['id']}/rest", headers=h).status_code == 200
    go(client, hero["id"], h, "nord")
    last = fight(client, hero["id"], h)  # liche
    assert last["issue"] == "monstre_vaincu" and last["victoire"] is True
    state = client.get(f"/heroes/{hero['id']}", headers=h).json()
    assert state["victoire"] is True and state["or_"] == 5 + 40 + 100


# --- Bonus : classement -------------------------------------------------------------


def test_leaderboard_public(client, auth, make_hero):
    h = auth()
    pauvre = make_hero(h, nom="Pauvre")
    riche = make_hero(h, nom="Riche")
    go(client, riche["id"], h, "nord", "est")
    fight(client, riche["id"], h)
    r = client.get("/leaderboard")  # sans token
    assert r.status_code == 200
    noms = [e["nom"] for e in r.json()]
    assert noms == ["Riche", "Pauvre"]
    assert r.json()[0]["or_"] == 15 and r.json()[0]["joueur"] == "alice"
    assert "owner_id" not in r.text and "monstre_pv" not in r.text
