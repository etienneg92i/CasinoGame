"""Tests du profil persistant.

Couvre le ticket #2 (bankroll conservée entre sessions), le ticket #3
(historique des rounds en ajout seul) et le ticket #4 (re-buy au lancement
d'une session basse).

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


class EnregistrerMancheTest(unittest.TestCase):
    """Ticket #3 — chaque round ajoute exactement une entrée à ``history``, les
    entrées antérieures ne sont jamais touchées, et l'entrée est persistée dans
    la même écriture atomique que la bankroll."""

    def test_un_round_ajoute_exactement_une_entree(self):
        p = profil.Profil()

        profil.enregistrer_manche(
            p, mise=50.0, proximity=87.3, gain=76.12, net=26.12, house_edge=1.0
        )

        self.assertEqual(len(p.history), 1)

    def test_chaque_appel_ajoute_une_entree_dans_l_ordre_de_jeu(self):
        p = profil.Profil()

        for mise in (10.0, 20.0, 30.0):
            profil.enregistrer_manche(
                p, mise=mise, proximity=50.0, gain=0.0, net=-mise, house_edge=1.0
            )

        self.assertEqual([e["mise"] for e in p.history], [10.0, 20.0, 30.0])

    def test_les_entrees_anterieures_ne_sont_jamais_modifiees_ni_retirees(self):
        ancienne = {
            "timestamp": "2026-01-01T00:00:00Z",
            "mise": 5.0,
            "proximity": 12.0,
            "gain": 0.0,
            "net": -5.0,
            "house_edge": 1.0,
        }
        p = profil.Profil(history=[dict(ancienne)])

        profil.enregistrer_manche(
            p, mise=99.0, proximity=95.0, gain=188.1, net=89.1, house_edge=1.3
        )

        self.assertEqual(p.history[0], ancienne)
        self.assertEqual(len(p.history), 2)

    def test_contenu_d_une_entree(self):
        p = profil.Profil()

        fige = mock.Mock()
        fige.strftime.return_value = "2026-09-10T14:32:05Z"
        with mock.patch.object(profil, "datetime") as horloge:
            horloge.now.return_value = fige
            profil.enregistrer_manche(
                p, mise=50.0, proximity=87.3, gain=76.12, net=26.12, house_edge=1.0
            )

        self.assertEqual(
            p.history[-1],
            {
                "timestamp": "2026-09-10T14:32:05Z",
                "mise": 50.0,
                "proximity": 87.3,
                "gain": 76.12,
                "net": 26.12,
                "house_edge": 1.0,
            },
        )

    def test_horodatage_est_en_utc_iso_8601_avec_un_z_final(self):
        p = profil.Profil()

        profil.enregistrer_manche(
            p, mise=1.0, proximity=1.0, gain=0.0, net=-1.0, house_edge=1.0
        )

        horodatage = p.history[-1]["timestamp"]
        self.assertRegex(horodatage, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        # Analysable comme un instant UTC.
        from datetime import datetime, timezone

        lu = datetime.strptime(horodatage, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        self.assertEqual(lu.tzinfo, timezone.utc)


class AppliquerRecaveTest(unittest.TestCase):
    """Ticket #4 — au lancement d'une session, une bankroll sous le seuil est
    renflouée à SOLDE_INITIAL et ``re_buys`` est incrémenté ; au-dessus du seuil
    rien ne bouge. La fonction ne persiste pas par elle-même."""

    def test_sous_le_seuil_renfloue_et_renvoie_le_montant_injecte(self):
        p = profil.Profil(bankroll=3.33, re_buys=1)

        montant = profil.appliquer_recave(p)

        self.assertEqual(montant, round(profil.SOLDE_INITIAL - 3.33, 2))
        self.assertEqual(p.bankroll, profil.SOLDE_INITIAL)
        self.assertEqual(p.re_buys, 2)

    def test_bankroll_a_zero_est_renflouee(self):
        p = profil.Profil(bankroll=0.0)

        montant = profil.appliquer_recave(p)

        self.assertEqual(montant, profil.SOLDE_INITIAL)
        self.assertEqual(p.bankroll, profil.SOLDE_INITIAL)
        self.assertEqual(p.re_buys, 1)

    def test_pile_au_seuil_ne_declenche_pas_de_recave(self):
        p = profil.Profil(bankroll=profil.SEUIL_RECAVE, re_buys=4)

        montant = profil.appliquer_recave(p)

        self.assertIsNone(montant)
        self.assertEqual(p.bankroll, profil.SEUIL_RECAVE)
        self.assertEqual(p.re_buys, 4)

    def test_au_dessus_du_seuil_ne_touche_a_rien(self):
        p = profil.Profil(bankroll=742.5, re_buys=2, history=[{"net": 1.0}])

        montant = profil.appliquer_recave(p)

        self.assertIsNone(montant)
        self.assertEqual(p.bankroll, 742.5)
        self.assertEqual(p.re_buys, 2)
        self.assertEqual(p.history, [{"net": 1.0}])

    def test_la_recave_n_ajoute_aucune_entree_a_l_historique(self):
        p = profil.Profil(bankroll=1.0, history=[{"net": -5.0}])

        profil.appliquer_recave(p)

        self.assertEqual(p.history, [{"net": -5.0}])

    def test_ne_persiste_pas_par_elle_meme(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        chemin = Path(tmp.name) / "profil.json"

        profil.appliquer_recave(profil.Profil(bankroll=2.0))

        self.assertFalse(chemin.exists())

    def test_re_buys_persiste_via_sauvegarder_et_survit_a_un_redemarrage(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        chemin = Path(tmp.name) / "profil.json"

        session1 = profil.charger_profil(chemin)
        session1.bankroll = 4.0
        profil.appliquer_recave(session1)
        profil.sauvegarder(session1, chemin)

        session2 = profil.charger_profil(chemin)

        self.assertEqual(session2.re_buys, 1)
        self.assertEqual(session2.bankroll, profil.SOLDE_INITIAL)


class HistoriquePersisteTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.chemin = Path(tmp.name) / "profil.json"

    def test_l_entree_est_persistee_dans_la_meme_ecriture_que_la_bankroll(self):
        p = profil.charger_profil(self.chemin)
        p.bankroll = 812.5
        profil.enregistrer_manche(
            p, mise=40.0, proximity=70.0, gain=56.0, net=16.0, house_edge=1.0
        )

        profil.sauvegarder(p, self.chemin)

        sur_disque = json.loads(self.chemin.read_text(encoding="utf-8"))
        self.assertEqual(sur_disque["bankroll"], 812.5)
        self.assertEqual(len(sur_disque["history"]), 1)
        self.assertEqual(sur_disque["history"][0]["net"], 16.0)

    def test_plusieurs_rounds_puis_relecture_toutes_les_entrees_dans_l_ordre(self):
        p = profil.charger_profil(self.chemin)
        for i in range(1, 6):
            profil.enregistrer_manche(
                p,
                mise=float(i * 10),
                proximity=float(i * 5),
                gain=0.0,
                net=float(-i),
                house_edge=1.0,
            )
            profil.sauvegarder(p, self.chemin)

        relu = profil.charger_profil(self.chemin)

        self.assertEqual([e["mise"] for e in relu.history], [10.0, 20.0, 30.0, 40.0, 50.0])


if __name__ == "__main__":
    unittest.main()
