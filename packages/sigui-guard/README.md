# sigui-guard

**Une fonction. Un verdict. Zéro blockchain.**

`sigui-guard` répond à une seule question : *cette action d'agent est-elle sûre ?*
Il renvoie `ALLOW`, `BLOCK` ou `ESCALATE` — **hors ligne**, sans wallet, sans clé
privée, sans DID, sans enregistrement, sans appel réseau.

Le moteur local n'utilise que la bibliothèque standard de Python : **aucune
dépendance runtime** à installer.

> Ce paquet est le **SDK** (`check_action()`). Il est distinct du *proxy RPC*
> décrit dans `docs/SIGUI_GUARD.md` (interception de `eth_sendRawTransaction`), et
> de la couche protocole ERC-8259 / ZK / oracles, qui reste **optionnelle** et se
> consomme via `check_action(engine="hosted")` — jamais en prérequis.

---

## Installation

Depuis ce dépôt :

```bash
pip install ./packages/sigui-guard
```

---

## Démarrage en 10 lignes

```python
from sigui_guard import check_action

verdict = check_action(
    action_type="transfer",      # "transfer", "swap", "contract_interaction", ...
    amount_usd=500,              # montant en USD
    destination="0xabc...",      # adresse / identifiant de la cible
    agent_context={              # optionnel : signaux et historique connus
        "avg_amount_usd": 12.0,
        "tx_count": 240,
        "trust_score": 0.9,
    },
)

if verdict.blocked:              # la seule chose à tester pour bloquer
    raise RuntimeError(verdict.reason)
```

Aucune clé, aucun wallet, aucun `await`, aucun réseau. Le premier appel renvoie
un vrai verdict.

Exemple exécutable de bout en bout (un `ALLOW` et un `BLOCK` avec latence
mesurée) : [`examples/quickstart.py`](examples/quickstart.py).

```bash
python packages/sigui-guard/examples/quickstart.py
```

---

## Ce que renvoie un verdict

| Champ | Sens |
|---|---|
| `verdict.decision` | `"ALLOW"` / `"BLOCK"` / `"ESCALATE"` — le verdict calculé |
| `verdict.blocked` | `bool` — **ce que l'appelant doit respecter** |
| `verdict.engine` | `"local"` ou `"hosted"` — qui a rendu le verdict (jamais mensonger) |
| `verdict.reason` | explication lisible en une phrase |
| `verdict.risk_score` | score de risque dans `[0, 1]` |
| `verdict.rules_triggered` | règles ayant contribué à la décision |
| `verdict.latency_ms` | temps de calcul réel, en millisecondes |
| `verdict.to_dict()` | l'objet complet, sérialisable en JSON |

**Règle d'or :** pour bloquer, testez `verdict.blocked`, **jamais**
`verdict.decision`. En mode `shadow`, `decision` reste le verdict calculé mais
`blocked` vaut toujours `False`.

---

## Modes et options

| Argument | Valeurs | Effet |
|---|---|---|
| `mode` | `"enforce"` (défaut), `"shadow"` | `shadow` observe sans jamais bloquer |
| `engine` | `"local"` (défaut), `"hosted"` | `hosted` appelle la couche protocole Sigui |
| `on_hosted_failure` | `"fallback_local"` (défaut), `"block"` | comportement si le service hébergé est injoignable |
| `allow_threshold` / `block_threshold` | `float` | surcharge des seuils de politique |

---

## Signaux reconnus dans `agent_context`

Tous optionnels. Plus vous en fournissez, plus le verdict est précis :

`avg_amount_usd`, `tx_count`, `trust_score`, `frequency_last_minute`,
`cumulative_flow`, `global_flow`, `service_eval`, `contract_eval`,
`known_safe`, `blacklist`, `pattern_risk`.

Sans contexte, le moteur reste conservateur : il bloque les cas manifestement
dangereux (destinations blacklistées, gros transferts vers l'inconnu) et autorise
le reste.

---

## Limite assumée du mode local

Le moteur local ne détecte **pas** les topologies on-chain avancées
(`DRAIN_STAR`, `MIXING_CHAIN`, `COORDINATED_CLUSTER`) : celles-ci nécessitent le
ThreatRegistry et le modèle de vision Imina-Na. C'est précisément la valeur
ajoutée de la couche protocole, accessible via `engine="hosted"`.

Le mode local reproduit, à l'identique, l'algorithme de décision de la
plateforme (voir `tests/test_engine_parity.py`, qui compare les deux moteurs cas
par cas et échoue à la moindre divergence).

---

## Licence

MIT.
