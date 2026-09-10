"""Profil persistant du joueur — un unique fichier JSON par machine.

Le profil conserve la bankroll et l'historique des rounds entre les sessions.
Il est implicite (aucun nom, aucune sélection au lancement) et il n'en existe
qu'un par machine.

Les fonctions publiques restent aussi pures que possible : le chemin du fichier
est leur seule entrée/sortie.

Voir docs/adr/0001-single-implicit-profile.md (profil unique implicite) et
docs/adr/0003-profile-storage.md (emplacement du fichier, écriture atomique).
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1

# Bankroll d'un profil neuf, et cible d'un re-buy (ADR-0002). Défini ici plutôt
# que dans casino_couleur.py : profil.py est le module bas niveau et ne peut pas
# importer casino_couleur.py sans créer un cycle d'imports.
SOLDE_INITIAL = 1000.0

# En dessous de ce solde au lancement d'une session, la banque renfloue le joueur
# jusqu'à SOLDE_INITIAL (ADR-0002). Défini ici pour la même raison que
# SOLDE_INITIAL : appliquer_recave en a besoin et vit dans ce module.
SEUIL_RECAVE = 10.0

_NOM_APPLICATION = "casino-teinte"
_NOM_FICHIER = "profil.json"


@dataclass
class Profil:
    """État persistant d'un joueur.

    ``bankroll`` est reportée après chaque round, ``history`` reçoit une entrée
    par round joué, et ``re_buys`` compte les renflouements de la banque au
    lancement d'une session (:func:`appliquer_recave`).
    """

    bankroll: float = SOLDE_INITIAL
    re_buys: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION


def resoudre_chemin() -> Path:
    """Chemin du fichier profil.

    ``CASINO_PROFILE_PATH`` a la priorité si elle est définie ; sinon le fichier
    vit dans le répertoire de données utilisateur de l'OS
    (``~/.local/share/casino-teinte/`` sous Linux/macOS,
    ``%APPDATA%\\casino-teinte\\`` sous Windows).
    """
    surcharge = os.environ.get("CASINO_PROFILE_PATH")
    if surcharge:
        return Path(surcharge).expanduser()
    return _repertoire_donnees() / _NOM_FICHIER


def _repertoire_donnees() -> Path:
    if os.name == "nt":
        base = os.environ.get("APPDATA")
        racine = Path(base) if base else Path.home() / "AppData" / "Roaming"
    else:
        racine = Path.home() / ".local" / "share"
    return racine / _NOM_APPLICATION


def charger_profil(chemin: Path) -> Profil:
    """Charge le profil, ou en crée un neuf si le fichier n'existe pas encore.

    La quarantaine d'un fichier corrompu ou de version inconnue est traitée par
    une unité ultérieure (ADR-0003) ; ici une erreur de lecture ou de parsing se
    propage.
    """
    try:
        texte = Path(chemin).read_text(encoding="utf-8")
    except FileNotFoundError:
        return Profil()

    donnees = json.loads(texte)
    return Profil(
        bankroll=float(donnees["bankroll"]),
        re_buys=int(donnees.get("re_buys", 0)),
        history=list(donnees.get("history", [])),
        schema_version=int(donnees.get("schema_version", SCHEMA_VERSION)),
    )


def appliquer_recave(profil: Profil) -> float | None:
    """Renfloue le joueur si sa bankroll est trop basse **au lancement** d'une
    session.

    Si ``bankroll < SEUIL_RECAVE``, remet ``bankroll`` à ``SOLDE_INITIAL``,
    incrémente ``re_buys`` et renvoie le montant injecté par la banque (le
    delta). Sinon renvoie ``None`` et ne touche à rien.

    Le re-buy n'a lieu qu'au lancement, jamais en cours de partie : tomber à
    court pendant une session met fin à cette session, et l'appelant n'invoque
    cette fonction qu'une fois, avant la boucle de jeu (ADR-0002).

    Ne persiste pas par elle-même : l'appelant écrit le profil via
    :func:`sauvegarder`. Le re-buy est de l'argent de la banque injecté hors
    jeu ; il est compté par ``re_buys`` seul et n'apparaît jamais dans
    ``history`` ni dans le net à vie.
    """
    if profil.bankroll >= SEUIL_RECAVE:
        return None
    montant = round(SOLDE_INITIAL - profil.bankroll, 2)
    profil.bankroll = SOLDE_INITIAL
    profil.re_buys += 1
    return montant


def enregistrer_manche(
    profil: Profil,
    *,
    mise: float,
    proximity: float,
    gain: float,
    net: float,
    house_edge: float,
) -> None:
    """Ajoute **une** entrée à ``profil.history`` pour le round qui vient d'être
    joué.

    L'historique est en ajout seul et non borné (ADR-0003) : les entrées déjà
    présentes ne sont jamais modifiées ni retirées, seule une nouvelle entrée est
    ajoutée en fin de liste, dans l'ordre de jeu. Chaque entrée capture de quoi
    recalculer tous les agrégats à vie ; l'horodatage est l'instant courant en
    UTC, ISO 8601 avec un « Z » final.

    Ne persiste pas par elle-même : l'appelant écrit le profil (bankroll +
    history) dans la même sauvegarde atomique via :func:`sauvegarder`.
    """
    profil.history.append(
        {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "mise": mise,
            "proximity": proximity,
            "gain": gain,
            "net": net,
            "house_edge": house_edge,
        }
    )


def sauvegarder(profil: Profil, chemin: Path) -> None:
    """Écrit le profil de façon atomique : fichier temporaire + ``os.replace``.

    Le fichier définitif n'est jamais observé à moitié écrit ; en cas d'échec le
    fichier temporaire est nettoyé et l'ancien profil reste intact. Le
    répertoire parent est créé au besoin.
    """
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    donnees = {
        "schema_version": profil.schema_version,
        "bankroll": profil.bankroll,
        "re_buys": profil.re_buys,
        "history": profil.history,
    }

    fd, temporaire = tempfile.mkstemp(
        dir=chemin.parent, prefix=chemin.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as flux:
            json.dump(donnees, flux, ensure_ascii=False, indent=2)
            flux.flush()
            os.fsync(flux.fileno())
        os.replace(temporaire, chemin)
    except BaseException:
        try:
            os.unlink(temporaire)
        except OSError:
            pass
        raise
