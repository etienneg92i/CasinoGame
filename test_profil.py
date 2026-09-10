"""Tests du profil persistant — ticket #2 (bankroll conservée entre sessions).

Framework : ``unittest`` de la bibliothèque standard — le projet ne dépend
d'aucune bibliothèque tierce (spec, issue #1, « Testing Decisions »).
Lancement : ``python -m unittest``
"""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import profil


class ResoudreCheminTest(unittest.TestCase):
    def test_casino_profile_path_est_prioritaire(self):
        with mock.patch.dict(
            os.environ, {"CASINO_PROFILE_PATH": "/tmp/ailleurs/mon-profil.json"}
        ):
            self.assertEqual(
                profil.resoudre_chemin(), Path("/tmp/ailleurs/mon-profil.json")
            )

    def test_chemin_par_defaut_dans_le_repertoire_de_donnees_utilisateur(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("CASINO_PROFILE_PATH", None)
            with mock.patch.object(profil.os, "name", "posix"), mock.patch.object(
                profil.Path, "home", return_value=Path("/home/joueur")
            ):
                self.assertEqual(
                    profil.resoudre_chemin(),
                    Path("/home/joueur/.local/share/casino-teinte/profil.json"),
                )


class ProfilSurDisqueTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repertoire = Path(tmp.name)
        self.chemin = self.repertoire / "profil.json"

    def _residus(self):
        return [q.name for q in self.chemin.parent.iterdir() if q != self.chemin]

    # -- création d'un profil neuf ----------------------------------------- #

    def test_fichier_absent_donne_un_profil_neuf(self):
        p = profil.charger_profil(self.chemin)

        self.assertEqual(p.schema_version, profil.SCHEMA_VERSION)
        self.assertEqual(p.bankroll, profil.SOLDE_INITIAL)
        self.assertEqual(p.re_buys, 0)
        self.assertEqual(p.history, [])

    def test_charger_ne_cree_pas_le_fichier_tout_seul(self):
        profil.charger_profil(self.chemin)
        self.assertFalse(self.chemin.exists())

    # -- reprise depuis un profil existant -------------------------------- #

    def test_reprise_depuis_un_profil_existant(self):
        self.chemin.write_text(
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

        p = profil.charger_profil(self.chemin)

        self.assertEqual(p.bankroll, 742.5)
        self.assertEqual(p.re_buys, 2)
        self.assertEqual(p.history, [{"net": -10.0}])

    def test_aller_retour_sauvegarder_puis_charger(self):
        p = profil.Profil(bankroll=333.33, re_buys=1, history=[{"proximity": 80.0}])
        profil.sauvegarder(p, self.chemin)

        relu = profil.charger_profil(self.chemin)

        self.assertEqual(relu.bankroll, 333.33)
        self.assertEqual(relu.re_buys, 1)
        self.assertEqual(relu.history, [{"proximity": 80.0}])
        self.assertEqual(relu.schema_version, profil.SCHEMA_VERSION)

    def test_quitter_puis_relancer_reprend_le_solde_laisse(self):
        session1 = profil.charger_profil(self.chemin)
        session1.bankroll -= 120.0
        profil.sauvegarder(session1, self.chemin)

        session2 = profil.charger_profil(self.chemin)

        self.assertEqual(session2.bankroll, profil.SOLDE_INITIAL - 120.0)

    # -- écriture atomique ----------------------------------------------- #

    def test_sauvegarde_produit_un_json_valide_et_complet(self):
        profil.sauvegarder(profil.Profil(bankroll=500.0), self.chemin)

        donnees = json.loads(self.chemin.read_text(encoding="utf-8"))
        self.assertEqual(
            donnees,
            {"schema_version": 1, "bankroll": 500.0, "re_buys": 0, "history": []},
        )

    def test_sauvegarde_cree_le_repertoire_parent_si_absent(self):
        chemin = self.repertoire / "pas" / "encore" / "la" / "profil.json"

        profil.sauvegarder(profil.Profil(), chemin)

        self.assertTrue(chemin.exists())

    def test_echec_pendant_l_ecriture_laisse_l_ancien_profil_intact(self):
        profil.sauvegarder(profil.Profil(bankroll=999.0), self.chemin)
        avant = self.chemin.read_text(encoding="utf-8")

        with mock.patch.object(
            profil.json, "dump", side_effect=RuntimeError("disque plein")
        ):
            with self.assertRaises(RuntimeError):
                profil.sauvegarder(profil.Profil(bankroll=1.0), self.chemin)

        # Le fichier définitif est soit l'ancien contenu, soit le nouveau, jamais
        # tronqué — ici l'ancien, et aucun fichier temporaire ne subsiste.
        self.assertEqual(self.chemin.read_text(encoding="utf-8"), avant)
        self.assertEqual(self._residus(), [])

    def test_sauvegarde_ne_laisse_pas_de_fichier_temporaire(self):
        profil.sauvegarder(profil.Profil(), self.chemin)
        self.assertEqual(self._residus(), [])


if __name__ == "__main__":
    unittest.main()
