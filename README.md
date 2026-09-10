# Casino de la teinte 🎨

Jeu de casino en Python (terminal). Le joueur mise sur une **teinte** du cercle
chromatique ; la banque tire une couleur au hasard à partir de l'**entropie
quantique** du générateur [ANU QRNG](https://qrng.anu.edu.au/random-colours/).
Le gain dépend de la proximité entre la teinte misée et la teinte tirée.

## Lancer

```
python casino_couleur.py
```

Aucune dépendance : uniquement la bibliothèque standard (Python ≥ 3.10).
Un terminal gérant les couleurs 24 bits est recommandé (Windows Terminal,
iTerm2, la plupart des terminaux Linux).

## Règles

1. Vous misez un montant sur une teinte, exprimée soit par un **angle 0–359°**,
   soit par un **nom** : `rouge`, `orange`, `jaune`, `vert`, `turquoise`,
   `cyan`, `bleu`, `indigo`, `violet`, `magenta`, `rose`…
2. La banque tire 3 octets quantiques (R, V, B) → une couleur.
3. On calcule la distance angulaire entre les deux teintes sur le cercle
   (0° à 180°), puis la proximité en pourcentage :

   ```
   proximité (%) = (1 − distance / 180) × 100
   ```

   - `100 %` : teinte identique
   - `50 %`  : teintes à 90° (ex. rouge vs vert-jaune)
   - `0 %`   : teintes opposées (ex. rouge vs cyan)

4. Gain :

   ```
   gain = mise × 2 × (proximité / 100) ^ exposant
   ```

   Avec l'exposant par défaut `1.0`, le jeu est **équitable** : une mise de
   50 € rapporte de **0 € à 100 €**, et l'espérance de gain d'un joueur qui
   choisit une teinte au hasard vaut exactement sa mise.

### Avantage maison

```
python casino_couleur.py --avantage-maison 1.3
```

Un exposant supérieur à 1 courbe le barème en faveur de la banque
(ex. avec `1.3`, l'espérance de gain d'un joueur au hasard tombe à ~87 % de
sa mise, soit ~13 % d'avantage maison).

## Profil

Le jeu conserve un **profil** unique par machine : un fichier JSON qui retient
la **bankroll** d'une session à l'autre. Vous ne repartez pas de 1000 € à
chaque lancement, mais du solde laissé par la session précédente.

Emplacement du fichier :

- Linux / macOS : `~/.local/share/casino-teinte/profil.json`
- Windows : `%APPDATA%\casino-teinte\profil.json`
- ou le chemin indiqué par la variable d'environnement `CASINO_PROFILE_PATH`

Le fichier est réécrit après chaque round, de façon atomique (il n'est jamais
observé à moitié écrit). Voir `docs/adr/0001-single-implicit-profile.md` et
`docs/adr/0003-profile-storage.md`.

## Source d'entropie

`quantum_entropy.py` tente, dans l'ordre :

1. **API moderne** `api.quantumnumbers.anu.edu.au` — nécessite une clé
   gratuite, à placer dans la variable d'environnement `ANU_API_KEY`
   (inscription : https://quantumnumbers.anu.edu.au/).
2. **API historique** `qrng.anu.edu.au/API/jsonI.php` — sans clé, souvent
   limitée en débit.
3. **Repli local** `secrets.token_bytes` — CSPRNG du système (non quantique).

Pour interdire le repli local et exiger une source quantique :

```
set CASINO_REQUIRE_QUANTUM=1      # PowerShell : $env:CASINO_REQUIRE_QUANTUM=1
```

Le jeu indique à chaque tirage la source réellement utilisée.

## Fichiers

| Fichier               | Rôle                                             |
|-----------------------|--------------------------------------------------|
| `casino_couleur.py`   | Jeu : boucle, roue chromatique, barème, saisies  |
| `quantum_entropy.py`  | Récupération des octets aléatoires ANU QRNG      |
| `profil.py`           | Profil persistant : chemin, chargement, écriture |
