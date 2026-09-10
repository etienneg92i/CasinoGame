"""Tests du profil persistant (ticket #2)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import profil


@pytest.fixture(autouse=True)
def profil_isole(tmp_path, monkeypatch):
    """Isole chaque test dans son propre fichier profil via CASINO_PROFILE_PATH."""
    chemin = tmp_path / "profil.json"
    monkeypatch.setenv("CASINO_PROFILE_PATH", str(chemin))
    return chemin


# --------------------------------------------------------------------------- #
# Résolution du chemin
# --------------------------------------------------------------------------- #


def test_chemin_prend_en_compte_casino_profile_path(profil_isole):
    assert profil.chemin_profil() == profil_isole


def test_casino_profile_path_a_la_priorite_sur_le_repertoire_os(monkeypatch, tmp_path):
    surcharge = tmp_path / "ailleurs" / "mon-profil.json"
    monkeypatch.setenv("CASINO_PROFILE_PATH", str(surcharge))
    assert profil.chemin_profil() == surcharge


def test_chemin_par_defaut_dans_le_repertoire_de_donnees_utilisateur(monkeypatch):
    monkeypatch.delenv("CASINO_PROFILE_PATH", raising=False)
    monkeypatch.setattr(os, "name", "posix")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: Path("/home/joueur")))

    assert profil.chemin_profil() == Path(
        "/home/joueur/.local/share/casino-teinte/profil.json"
    )


# --------------------------------------------------------------------------- #
# Création d'un profil neuf
# --------------------------------------------------------------------------- #


def test_fichier_absent_cree_un_profil_neuf(profil_isole):
    assert not profil_isole.exists()

    p = profil.charger()

    assert p.schema_version == profil.SCHEMA_VERSION
    assert p.bankroll == 1000.0
    assert p.re_buys == 0
    assert p.history == []


def test_charger_ne_cree_pas_le_fichier_tout_seul(profil_isole):
    profil.charger()
    assert not profil_isole.exists()


# --------------------------------------------------------------------------- #
# Reprise depuis un profil existant
# --------------------------------------------------------------------------- #


def test_reprise_depuis_un_profil_existant(profil_isole):
    profil_isole.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "bankroll": 742.5,
                "re_buys": 2,
                "history": [{"net": -10.0}],
            }
        ),
        encoding="utf-8",
    )

    p = profil.charger()

    assert p.bankroll == 742.5
    assert p.re_buys == 2
    assert p.history == [{"net": -10.0}]


def test_aller_retour_sauvegarder_puis_charger(profil_isole):
    p = profil.Profil(bankroll=333.33, re_buys=1, history=[{"proximite": 80.0}])
    profil.sauvegarder(p)

    relu = profil.charger()

    assert relu.bankroll == 333.33
    assert relu.re_buys == 1
    assert relu.history == [{"proximite": 80.0}]
    assert relu.schema_version == profil.SCHEMA_VERSION


def test_quitter_puis_relancer_reprend_le_solde_laisse(profil_isole):
    # Session 1 : on part de 1000 et on termine à 880.
    session1 = profil.charger()
    session1.bankroll -= 120.0
    profil.sauvegarder(session1)

    # Session 2 : nouveau chargement, on doit repartir de 880.
    session2 = profil.charger()
    assert session2.bankroll == 880.0


# --------------------------------------------------------------------------- #
# Écriture atomique
# --------------------------------------------------------------------------- #


def test_sauvegarde_produit_un_fichier_json_valide(profil_isole):
    profil.sauvegarder(profil.Profil(bankroll=500.0))

    donnees = json.loads(profil_isole.read_text(encoding="utf-8"))
    assert donnees == {
        "schema_version": 1,
        "bankroll": 500.0,
        "re_buys": 0,
        "history": [],
    }


def test_sauvegarde_cree_le_repertoire_parent_si_absent(tmp_path, monkeypatch):
    chemin = tmp_path / "pas" / "encore" / "la" / "profil.json"
    monkeypatch.setenv("CASINO_PROFILE_PATH", str(chemin))

    profil.sauvegarder(profil.Profil())

    assert chemin.exists()


def test_echec_pendant_l_ecriture_laisse_l_ancien_profil_intact(
    profil_isole, monkeypatch
):
    profil.sauvegarder(profil.Profil(bankroll=999.0))
    avant = profil_isole.read_text(encoding="utf-8")

    def json_dump_qui_casse(*_args, **_kwargs):
        raise RuntimeError("disque plein")

    monkeypatch.setattr(profil.json, "dump", json_dump_qui_casse)

    with pytest.raises(RuntimeError):
        profil.sauvegarder(profil.Profil(bankroll=1.0))

    # L'ancien fichier n'a pas bougé et aucun fichier temporaire ne traîne.
    assert profil_isole.read_text(encoding="utf-8") == avant
    residus = [q for q in profil_isole.parent.iterdir() if q != profil_isole]
    assert residus == []


def test_sauvegarde_ne_laisse_pas_de_fichier_temporaire(profil_isole):
    profil.sauvegarder(profil.Profil())

    residus = [q for q in profil_isole.parent.iterdir() if q != profil_isole]
    assert residus == []
