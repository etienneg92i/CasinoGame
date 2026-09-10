"""Intégration jeu ↔ profil : la bankroll circule et se persiste (ticket #2)."""

from __future__ import annotations

import pytest

import casino_couleur
import profil


@pytest.fixture(autouse=True)
def profil_isole(tmp_path, monkeypatch):
    monkeypatch.setenv("CASINO_PROFILE_PATH", str(tmp_path / "profil.json"))


def _entropie_fixe(rgb):
    return lambda: (rgb, "source de test", False)


def test_un_round_gagnant_reporte_le_gain_sur_la_bankroll(monkeypatch):
    reponses = iter(["100", "0", ""])  # mise, teinte rouge, [Entrée]
    monkeypatch.setattr(casino_couleur, "demander", lambda _q: next(reponses))
    monkeypatch.setattr(casino_couleur, "tirer_couleur", _entropie_fixe((255, 0, 0)))

    p = profil.Profil(bankroll=1000.0)
    casino_couleur.jouer_manche(p, exposant=1.0)

    # Teinte identique → proximité 100 % → gain = 2 × mise → net = +100.
    assert p.bankroll == 1100.0


def test_interruption_pendant_la_saisie_laisse_la_bankroll_intacte(monkeypatch):
    def demander_qui_interrompt(_q):
        raise KeyboardInterrupt

    monkeypatch.setattr(casino_couleur, "demander", demander_qui_interrompt)

    p = profil.Profil(bankroll=1000.0)
    with pytest.raises(KeyboardInterrupt):
        casino_couleur.jouer_manche(p, exposant=1.0)

    assert p.bankroll == 1000.0


def test_la_bankroll_est_persistee_apres_chaque_round(monkeypatch):
    reponses = iter(["100", "0", "", "n"])  # round gagnant puis « non » pour arrêter
    monkeypatch.setattr(casino_couleur, "demander", lambda _q: next(reponses))
    monkeypatch.setattr(casino_couleur, "tirer_couleur", _entropie_fixe((255, 0, 0)))
    monkeypatch.setattr(casino_couleur, "preparer_terminal", lambda: None)

    casino_couleur.boucle_jeu(exposant=1.0)

    assert profil.charger().bankroll == 1100.0
