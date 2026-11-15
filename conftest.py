"""
Racine du dépôt — configuration partagée par pytest.

Le SDK `sigui_guard` vit désormais dans `packages/sigui-guard/` (son propre
projet pip-installable), et non plus à la racine. Ce conftest rend le paquet
importable pour l'ensemble des tests du dépôt (`tests/test_sigui_guard_sdk.py`,
`tests/test_engine_parity.py`) sans rien changer à leur code.

Un développeur externe n'a pas besoin de ce fichier : après
`pip install ./packages/sigui-guard`, `import sigui_guard` fonctionne partout.
Ici, il ne sert qu'aux tests in-repo, qui tournent sur les sources.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SDK_DIR = Path(__file__).resolve().parent / "packages" / "sigui-guard"

if _SDK_DIR.is_dir() and str(_SDK_DIR) not in sys.path:
    sys.path.insert(0, str(_SDK_DIR))
