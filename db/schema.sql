-- ArcWarden v3.0 — SQLite Schema
-- MemoClaw Memory Layer

-- Profil et réputation de chaque agent client
CREATE TABLE IF NOT EXISTS agents (
    agent_id        TEXT PRIMARY KEY,
    wallet_address  TEXT NOT NULL,
    trust_score     REAL DEFAULT 0.5,
    tx_count        INTEGER DEFAULT 0,
    avg_amount_usdc REAL DEFAULT 0.0,
    total_blocked   INTEGER DEFAULT 0,
    last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Patterns d'attaque reconnus par ArcWarden
CREATE TABLE IF NOT EXISTS patterns (
    pattern_id  TEXT PRIMARY KEY,
    signature   TEXT NOT NULL,
    risk_weight REAL DEFAULT 0.30,
    occurrences INTEGER DEFAULT 1,
    first_seen  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historique complet de toutes les décisions
CREATE TABLE IF NOT EXISTS decisions (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id           TEXT NOT NULL,
    action_type        TEXT NOT NULL,
    amount_usdc        REAL DEFAULT 0.0,
    destination        TEXT DEFAULT '',
    action_hash        TEXT NOT NULL,
    decision           TEXT NOT NULL,
    risk_score         REAL NOT NULL,
    confidence         REAL DEFAULT 0.0,
    chain              TEXT DEFAULT 'arc',
    rules_triggered    TEXT DEFAULT '[]',
    arc_tx_hash        TEXT DEFAULT '',
    arcwarden_mode     TEXT DEFAULT 'NORMAL',
    processing_time_ms INTEGER DEFAULT 0,
    timestamp          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Registre des attaques bloquées et USDC protégés
CREATE TABLE IF NOT EXISTS attacks (
    attack_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id             TEXT NOT NULL,
    agent_id               TEXT NOT NULL,
    blocked_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    amount_attempted_usdc  REAL NOT NULL,
    amount_saved_usdc      REAL NOT NULL
);

-- Journal de trésorerie ArcWarden
CREATE TABLE IF NOT EXISTS treasury_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    amount_usdc REAL NOT NULL,
    chain       TEXT DEFAULT 'arc',
    description TEXT DEFAULT '',
    timestamp   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mémoire épisodique des décisions et outcomes observés
CREATE TABLE IF NOT EXISTS episodic_memory (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL,
    action_type     TEXT NOT NULL,
    decision        TEXT NOT NULL,
    risk_score      REAL NOT NULL,
    policy_source   TEXT DEFAULT 'rules',
    outcome_label   TEXT DEFAULT 'unknown',
    notes           TEXT DEFAULT '',
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Historique des ajustements de policy autonomes
CREATE TABLE IF NOT EXISTS policy_updates (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    allow_threshold         REAL NOT NULL,
    block_threshold         REAL NOT NULL,
    rationale               TEXT DEFAULT '',
    source                  TEXT DEFAULT 'self_critique',
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Gel temporaire d'agents (survit aux redémarrages)
CREATE TABLE IF NOT EXISTS agent_freeze (
    agent_id     TEXT PRIMARY KEY,
    frozen_until TIMESTAMP NOT NULL,
    reason       TEXT DEFAULT '',
    block_count  INTEGER DEFAULT 1,
    frozen_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Blacklist persistante d'adresses malveillantes
CREATE TABLE IF NOT EXISTS blacklist (
    address   TEXT PRIMARY KEY,
    reason    TEXT DEFAULT '',
    added_by  TEXT DEFAULT 'system',
    added_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_decisions_agent    ON decisions(agent_id);
CREATE INDEX IF NOT EXISTS idx_decisions_ts       ON decisions(timestamp);
CREATE INDEX IF NOT EXISTS idx_patterns_weight    ON patterns(risk_weight DESC);
CREATE INDEX IF NOT EXISTS idx_treasury_type      ON treasury_log(type);
CREATE INDEX IF NOT EXISTS idx_episodic_ts        ON episodic_memory(timestamp);
CREATE INDEX IF NOT EXISTS idx_policy_updates_ts  ON policy_updates(created_at);
CREATE INDEX IF NOT EXISTS idx_freeze_until       ON agent_freeze(frozen_until);
CREATE INDEX IF NOT EXISTS idx_blacklist_addr     ON blacklist(address);

-- Historique des actions du DAO Hogonat
CREATE TABLE IF NOT EXISTS hogonat_history (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    action_type     TEXT NOT NULL,
    staker_id       TEXT,
    amount_usdc     REAL DEFAULT 0.0,
    details         TEXT DEFAULT '',
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_hogonat_ts         ON hogonat_history(timestamp);

-- ── Fenêtre glissante anti-splitting (transaction fragmentation detection) ────
CREATE TABLE IF NOT EXISTS flow_windows (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL,
    destination     TEXT NOT NULL,
    chain           TEXT NOT NULL DEFAULT 'arc',
    amount_usdc     REAL NOT NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour performance
CREATE INDEX IF NOT EXISTS idx_flow_agent_dest
    ON flow_windows (agent_id, destination, timestamp);

-- ── Service Registry (réputation des services/API destinataires) ────────────
CREATE TABLE IF NOT EXISTS service_registry (
    address         TEXT PRIMARY KEY,
    name            TEXT,
    trust_level     TEXT DEFAULT 'NEUTRAL',
    category        TEXT DEFAULT 'unknown',
    total_received  REAL DEFAULT 0.0,
    unique_payers   INTEGER DEFAULT 0,
    complaints      INTEGER DEFAULT 0,
    first_seen      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tags            TEXT DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS service_interactions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id        TEXT NOT NULL,
    service_address TEXT NOT NULL,
    amount_usdc     REAL NOT NULL,
    outcome         TEXT NOT NULL,
    timestamp       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_svc_interactions_addr
    ON service_interactions (service_address, outcome, timestamp);

-- ── Replay attack protection — hashes de paiement déjà consommés ─────────────
-- Persisté en SQLite pour survivre aux redémarrages du serveur.
-- En mémoire vive (set Python) pour la performance intra-session.
CREATE TABLE IF NOT EXISTS used_payment_hashes (
    tx_hash    TEXT PRIMARY KEY,
    used_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    agent_id   TEXT DEFAULT ''   -- agent qui a soumis ce paiement
);

CREATE INDEX IF NOT EXISTS idx_used_hashes_ts
    ON used_payment_hashes (used_at);

-- ── Historique des validations de réponses (Response Validator) ──────────────
-- Stocke les résultats de chaque appel à POST /validate-response.
-- Permet la détection de patterns historiques (layer 4 du Response Validator).
CREATE TABLE IF NOT EXISTS response_validations (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_id               TEXT NOT NULL,
    service_address        TEXT NOT NULL,
    request_type           TEXT NOT NULL DEFAULT 'generic',
    verdict                TEXT NOT NULL,          -- SAFE | SUSPICIOUS | POISONED
    risk_score             REAL NOT NULL,
    findings_count         INTEGER DEFAULT 0,
    primary_numeric_value  REAL,                   -- valeur numérique extraite de la réponse
    processing_time_ms     INTEGER DEFAULT 0,
    timestamp              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_resp_val_service
    ON response_validations (service_address, request_type, timestamp);

CREATE INDEX IF NOT EXISTS idx_resp_val_agent
    ON response_validations (agent_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_resp_val_verdict
    ON response_validations (verdict, timestamp);
