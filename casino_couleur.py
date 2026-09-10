"""Casino de la teinte — misez sur une couleur du cercle chromatique.

Principe
--------
1. Vous misez un montant sur une teinte (angle 0-359 du cercle, ou un nom :
   « rouge », « bleu », « turquoise »...).
2. Le casino tire une couleur au hasard grâce à l'entropie quantique du
   générateur ANU QRNG (https://qrng.anu.edu.au/random-colours/).
3. On mesure la proximité entre votre teinte et celle tirée, en % :
       proximité = (1 - distance_angulaire / 180) * 100
   (0 % = teinte opposée sur le cercle, 100 % = teinte identique)
4. Gain = mise * 2 * (proximité / 100) ** EXPOSANT_PAIEMENT
   Avec EXPOSANT_PAIEMENT = 1.0 le jeu est équitable : une mise de 50 €
   rapporte de 0 € (raté) à 100 € (parfait), espérance = 50 €.
   Augmentez l'exposant (option --avantage-maison) pour créer un avantage
   pour la banque.

Lancement :  python casino_couleur.py
"""

from __future__ import annotations

import argparse
import colorsys
import math
import os
import sys

from profil import Profil, charger_profil, resoudre_chemin, sauvegarder
from quantum_entropy import get_quantum_bytes

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

EXPOSANT_PAIEMENT = 1.0  # 1.0 = équitable ; > 1.0 = avantage maison

TEINTES_NOMMEES = {
    "rouge": 0,
    "ecarlate": 5,
    "écarlate": 5,
    "vermillon": 12,
    "orange": 30,
    "ambre": 45,
    "or": 50,
    "jaune": 55,
    "citron": 70,
    "chartreuse": 90,
    "vert": 120,
    "emeraude": 150,
    "émeraude": 150,
    "turquoise": 170,
    "cyan": 180,
    "azur": 200,
    "bleu": 225,
    "outremer": 240,
    "indigo": 250,
    "violet": 275,
    "pourpre": 300,
    "magenta": 320,
    "rose": 335,
    "framboise": 345,
    "fuchsia": 325,
}


# --------------------------------------------------------------------------- #
# Terminal couleur
# --------------------------------------------------------------------------- #


def preparer_terminal() -> None:
    for flux in (sys.stdout, sys.stdin, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass
    activer_ansi_windows()


def activer_ansi_windows() -> None:
    if os.name != "nt":
        return
    try:
        import ctypes

        kernel32 = ctypes.windll.kernel32
        # ENABLE_PROCESSED_OUTPUT | ENABLE_WRAP_AT_EOL | ENABLE_VIRTUAL_TERMINAL_PROCESSING
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass


def pastille(r: int, g: int, b: int, largeur: int = 4) -> str:
    return f"\x1b[48;2;{r};{g};{b}m{' ' * largeur}\x1b[0m"


def texte_couleur(txt: str, r: int, g: int, b: int) -> str:
    return f"\x1b[38;2;{r};{g};{b}m{txt}\x1b[0m"


# --------------------------------------------------------------------------- #
# Couleurs et distances
# --------------------------------------------------------------------------- #


def teinte_vers_rgb(hue: float, s: float = 1.0, v: float = 1.0) -> tuple[int, int, int]:
    r, g, b = colorsys.hsv_to_rgb((hue % 360) / 360, s, v)
    return round(r * 255), round(g * 255), round(b * 255)


def rgb_vers_hsv(r: int, g: int, b: int) -> tuple[float, float, float]:
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return h * 360, s, v


def distance_teinte(a: float, b: float) -> float:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def proximite_pct(choisie: float, tiree: float) -> float:
    return (1 - distance_teinte(choisie, tiree) / 180) * 100


def gain(mise: float, proximite: float, exposant: float) -> float:
    return round(mise * 2 * (proximite / 100) ** exposant, 2)


def mention(proximite: float) -> str:
    for seuil, txt in (
        (95, "JACKPOT !"),
        (80, "Excellent"),
        (60, "Bien joué"),
        (40, "Correct"),
        (20, "Faible"),
    ):
        if proximite >= seuil:
            return txt
    return "Raté"


# --------------------------------------------------------------------------- #
# Roue chromatique ASCII (truecolor)
# --------------------------------------------------------------------------- #


def dessiner_roue(
    teinte_choisie: float, teinte_tiree: float | None = None, rayon: int = 13
) -> str:
    interieur, exterieur, milieu = 0.42, 1.0, 0.71
    marqueurs: dict[tuple[int, int], str] = {}

    def cellule_pour(hue: float) -> tuple[int, int]:
        theta = math.radians(hue)
        x = round(2 * rayon * milieu * math.cos(theta))
        y = round(-rayon * milieu * math.sin(theta))
        return x, y

    marqueurs[cellule_pour(teinte_choisie)] = "\x1b[1;38;2;255;255;255mX"
    if teinte_tiree is not None:
        marqueurs[cellule_pour(teinte_tiree)] = "\x1b[1;38;2;0;0;0mO"

    lignes = []
    for y in range(-rayon, rayon + 1):
        ligne = []
        for x in range(-2 * rayon, 2 * rayon + 1):
            dx = x / (2 * rayon)
            dy = y / rayon
            dist = math.hypot(dx, dy)
            if dist < interieur or dist > exterieur:
                ligne.append(" ")
                continue
            angle = math.degrees(math.atan2(-dy, dx)) % 360
            r, g, b = teinte_vers_rgb(angle, s=0.9, v=1.0)
            glyphe = marqueurs.get((x, y))
            contenu = glyphe if glyphe else " "
            ligne.append(f"\x1b[48;2;{r};{g};{b}m{contenu}\x1b[0m")
        lignes.append("".join(ligne))
    return "\n".join(lignes)


# --------------------------------------------------------------------------- #
# Saisies
# --------------------------------------------------------------------------- #


def lire_teinte(saisie: str) -> float:
    s = saisie.strip().lower()
    if s in TEINTES_NOMMEES:
        return float(TEINTES_NOMMEES[s])
    try:
        return float(s) % 360
    except ValueError as exc:
        raise ValueError(
            f"« {saisie} » n'est ni un angle (0-359) ni une teinte connue."
        ) from exc


def demander(question: str) -> str:
    try:
        return input(question)
    except EOFError:
        print()
        raise KeyboardInterrupt from None


# --------------------------------------------------------------------------- #
# Partie
# --------------------------------------------------------------------------- #


def tirer_couleur() -> tuple[tuple[int, int, int], str, bool]:
    res = get_quantum_bytes(3)
    r, g, b = res.data[0], res.data[1], res.data[2]
    return (r, g, b), res.source, res.quantum


def jouer_manche(profil: Profil, exposant: float) -> None:
    """Joue un round et reporte le résultat sur ``profil.bankroll``.

    La bankroll n'est modifiée qu'une fois le round entièrement résolu : une
    interruption en cours de saisie laisse le profil intact.
    """
    solde = profil.bankroll
    print("\n" + "=" * 60)
    print(f"  Solde : {texte_couleur(f'{solde:.2f} €', 120, 220, 120)}")
    print("=" * 60)

    # Mise
    while True:
        try:
            mise = float(demander("  Votre mise en € : ").replace(",", "."))
        except ValueError:
            print("  Montant invalide.")
            continue
        if mise <= 0:
            print("  La mise doit être positive.")
        elif mise > solde:
            print("  Solde insuffisant.")
        else:
            break

    # Teinte
    print("  Teinte : un angle 0-359, ou un nom (rouge, orange, jaune, vert,")
    print("           cyan, bleu, violet, magenta, rose, turquoise, indigo...)")
    while True:
        try:
            teinte_choisie = lire_teinte(demander("  Votre teinte : "))
            break
        except ValueError as exc:
            print(f"  {exc}")

    cr, cg, cb = teinte_vers_rgb(teinte_choisie)
    print(
        f"\n  Vous misez {mise:.2f} € sur "
        f"{pastille(cr, cg, cb)} teinte {teinte_choisie:.0f}°"
    )
    print(dessiner_roue(teinte_choisie))

    demander("\n  [Entrée] pour tirer la couleur quantique...")

    (r, g, b), source, quantique = tirer_couleur()
    h_tiree, s_tiree, v_tiree = rgb_vers_hsv(r, g, b)

    proximite = proximite_pct(teinte_choisie, h_tiree)
    montant = gain(mise, proximite, exposant)
    net = montant - mise

    print(f"\n  Entropie : {source}")
    print(dessiner_roue(teinte_choisie, h_tiree))
    print(
        f"\n  Couleur tirée : {pastille(r, g, b, 6)}  "
        f"RGB({r},{g},{b})  teinte {h_tiree:.0f}°  "
        f"saturation {s_tiree * 100:.0f}%"
    )
    print(f"  Votre teinte  : {pastille(cr, cg, cb, 6)}  teinte {teinte_choisie:.0f}°")
    if s_tiree < 0.12:
        print(
            texte_couleur(
                "  (couleur tirée quasi grise : sa teinte reste indicative)",
                200,
                200,
                120,
            )
        )

    barre_len = 40
    plein = round(barre_len * proximite / 100)
    barre = texte_couleur("█" * plein, 120, 220, 120) + "░" * (barre_len - plein)
    print(f"\n  Proximité : [{barre}] {proximite:.1f} %  — {mention(proximite)}")

    if net > 0:
        verdict = texte_couleur(f"GAIN  +{net:.2f} €", 120, 220, 120)
    elif net < 0:
        verdict = texte_couleur(f"PERTE {net:.2f} €", 230, 110, 110)
    else:
        verdict = "ÉQUILIBRE  0.00 €"
    print(f"  Gain brut : {montant:.2f} €   →   {verdict}")

    profil.bankroll = solde + net


def boucle_jeu(exposant: float) -> None:
    preparer_terminal()
    print(texte_couleur("\n  ♦ CASINO DE LA TEINTE ♦", 230, 200, 120))
    print("  Entropie quantique : ANU QRNG — https://qrng.anu.edu.au/random-colours/")
    if exposant != 1.0:
        print(
            texte_couleur(
                f"  Avantage maison actif (exposant de paiement = {exposant})",
                230,
                110,
                110,
            )
        )

    chemin_profil = resoudre_chemin()
    profil = charger_profil(chemin_profil)
    bankroll_depart = profil.bankroll
    manche = 0
    try:
        while profil.bankroll > 0:
            jouer_manche(profil, exposant)
            sauvegarder(profil, chemin_profil)
            manche += 1
            if profil.bankroll <= 0:
                print(texte_couleur("\n  Solde épuisé. Fin de partie.", 230, 110, 110))
                break
            if demander("\n  Rejouer ? [O/n] ").strip().lower() in ("n", "non"):
                break
    except KeyboardInterrupt:
        print("\n  Partie interrompue.")

    net = profil.bankroll - bankroll_depart
    couleur = (120, 220, 120) if net >= 0 else (230, 110, 110)
    print("\n" + "=" * 60)
    print(f"  {manche} manche(s) jouée(s)")
    print(
        f"  Solde final : {profil.bankroll:.2f} €   "
        f"({texte_couleur(f'{net:+.2f} €', *couleur)} vs début de session)"
    )
    print("=" * 60 + "\n")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Casino de la teinte (entropie quantique ANU)."
    )
    parser.add_argument(
        "--avantage-maison",
        type=float,
        default=EXPOSANT_PAIEMENT,
        metavar="EXPOSANT",
        help="Exposant de la courbe de paiement (1.0 = équitable, 1.3 ≈ 12 %% "
        "d'avantage pour la banque). Défaut : %(default)s",
    )
    args = parser.parse_args(argv)
    if args.avantage_maison <= 0:
        parser.error("l'exposant doit être strictement positif")
    boucle_jeu(args.avantage_maison)


if __name__ == "__main__":
    main()
