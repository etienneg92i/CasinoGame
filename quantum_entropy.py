"""Source d'entropie quantique — ANU QRNG (https://qrng.anu.edu.au/).

Récupère des octets aléatoires générés par mesure du vide quantique.
Ordre d'essai :
  1. API moderne  https://api.quantumnumbers.anu.edu.au  (nécessite une clé,
     variable d'environnement ANU_API_KEY)
  2. API historique  https://qrng.anu.edu.au/API/jsonI.php  (souvent limitée)
  3. Repli local  secrets.token_bytes  (CSPRNG du système d'exploitation)

Le repli peut être désactivé avec  CASINO_REQUIRE_QUANTUM=1  : dans ce cas une
exception est levée si le service ANU est injoignable.
"""

from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.request
from dataclasses import dataclass

ANU_LEGACY_API = "https://qrng.anu.edu.au/API/jsonI.php"
ANU_MODERN_API = "https://api.quantumnumbers.anu.edu.au"


@dataclass
class EntropyResult:
    data: bytes
    source: str
    quantum: bool


def _fetch_modern(n: int, api_key: str, timeout: float) -> bytes:
    url = f"{ANU_MODERN_API}?length={n}&type=uint8"
    req = urllib.request.Request(url, headers={"x-api-key": api_key})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    if not payload.get("success"):
        raise RuntimeError(f"réponse ANU sans succès : {payload}")
    return bytes(int(v) for v in payload["data"])


def _fetch_legacy(n: int, timeout: float) -> bytes:
    url = f"{ANU_LEGACY_API}?length={n}&type=uint8"
    req = urllib.request.Request(url, headers={"User-Agent": "casino-couleur/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = json.load(resp)
    if not payload.get("success"):
        raise RuntimeError(f"réponse ANU sans succès : {payload}")
    return bytes(int(v) for v in payload["data"])


def get_quantum_bytes(n: int = 3, timeout: float = 8.0) -> EntropyResult:
    """Renvoie `n` octets d'entropie et la description de leur origine."""
    require_quantum = os.environ.get("CASINO_REQUIRE_QUANTUM") == "1"
    api_key = os.environ.get("ANU_API_KEY")
    errors: list[str] = []

    if api_key:
        try:
            return EntropyResult(
                _fetch_modern(n, api_key, timeout),
                "ANU QRNG — api.quantumnumbers.anu.edu.au (vide quantique)",
                quantum=True,
            )
        except (urllib.error.URLError, OSError, ValueError, RuntimeError) as exc:
            errors.append(f"API moderne : {exc}")

    try:
        return EntropyResult(
            _fetch_legacy(n, timeout),
            "ANU QRNG — qrng.anu.edu.au (vide quantique)",
            quantum=True,
        )
    except (urllib.error.URLError, OSError, ValueError, RuntimeError) as exc:
        errors.append(f"API historique : {exc}")

    if require_quantum:
        raise RuntimeError(
            "Service ANU QRNG injoignable et CASINO_REQUIRE_QUANTUM=1 :\n  - "
            + "\n  - ".join(errors)
        )

    return EntropyResult(
        secrets.token_bytes(n),
        "repli local — secrets.token_bytes (CSPRNG système, non quantique)",
        quantum=False,
    )


if __name__ == "__main__":
    res = get_quantum_bytes(3)
    print(f"octets : {list(res.data)}")
    print(f"source : {res.source}")
