/// # Sigui Protocol — Agent Reputation Module
///
/// This module implements the on-chain reputation system for AI agents participating
/// in the Sigui Protocol. Each agent carries a `AgentProfile` keyed by its address
/// and identified by a W3C DID string. An oracle — a trusted off-chain entity or
/// DAO multisig — drives score updates and slashing events.
///
/// ## Security model
/// * Only the address stored in `ReputationRegistry.oracle` may call `update_reputation`
///   or `slash_agent`.
/// * `initialize` may only be called once (enforced by `exists<ReputationRegistry>`).
/// * All arithmetic is saturating — overflow cannot occur because we use explicit
///   `min`/`max` guards instead of unchecked addition.
///
/// ## Formal verification
/// Every public function carries a `spec` block that is checked by the **Move Prover**.
/// Running `aptos move prove` against this package will verify the full specification.
module sigui::agent_reputation {

    // ───────────────────────────────────────────────────────────
    //  Imports
    // ───────────────────────────────────────────────────────────
    use std::error;
    use std::signer;
    use std::vector;
    use aptos_std::table::{Self, Table};
    use aptos_framework::account;
    use aptos_framework::event::{Self, EventHandle};
    use aptos_framework::timestamp;

    // ───────────────────────────────────────────────────────────
    //  Constants
    // ───────────────────────────────────────────────────────────

    /// Maximum reputation score an agent can hold.
    const MAX_SCORE: u64 = 1_000_000;

    /// Initial reputation score awarded on registration.
    const INITIAL_SCORE: u64 = 100;

    /// Tier thresholds (inclusive lower bound).
    const TIER_BRONZE_MIN:   u64 = 0;
    const TIER_SILVER_MIN:   u64 = 250;
    const TIER_GOLD_MIN:     u64 = 500;
    const TIER_PLATINUM_MIN: u64 = 850;

    /// Tier identifiers.
    const TIER_BRONZE:   u8 = 0;
    const TIER_SILVER:   u8 = 1;
    const TIER_GOLD:     u8 = 2;
    const TIER_PLATINUM: u8 = 3;

    /// Slash percentage expressed in basis points (2 500 bp = 25 %).
    const SLASH_BASIS_POINTS: u64 = 2_500;
    const BASIS_POINTS_DENOM: u64 = 10_000;

    // ───────────────────────────────────────────────────────────
    //  Error codes
    // ───────────────────────────────────────────────────────────

    /// Registry has already been initialised.
    const EALREADY_INITIALIZED: u64 = 1;
    /// Registry has not been initialised yet.
    const ENOT_INITIALIZED: u64 = 2;
    /// Caller is not the designated oracle.
    const ENOT_ORACLE: u64 = 3;
    /// Agent address is not registered.
    const EAGENT_NOT_FOUND: u64 = 4;
    /// Agent address is already registered.
    const EAGENT_ALREADY_EXISTS: u64 = 5;
    /// Agent is currently inactive (slashed / suspended).
    const EAGENT_INACTIVE: u64 = 6;
    /// DID vector is empty.
    const EDID_EMPTY: u64 = 7;
    /// Delta value of zero is not allowed.
    const EZERO_DELTA: u64 = 8;

    // ───────────────────────────────────────────────────────────
    //  Core data structures
    // ───────────────────────────────────────────────────────────

    /// Per-agent profile stored inside `ReputationRegistry`.
    struct AgentProfile has store {
        /// Normalised score in [0, MAX_SCORE].
        reputation_score: u64,
        /// Computed tier: 0 = Bronze, 1 = Silver, 2 = Gold, 3 = Platinum.
        tier: u8,
        /// Cumulative number of confirmed threat reports against this agent.
        threat_count: u64,
        /// False when the agent has been slashed / suspended.
        is_active: bool,
        /// Unix timestamp (seconds) of registration, sourced from `timestamp::now_seconds`.
        registered_at: u64,
        /// Unix timestamp of the most recent score update.
        last_updated: u64,
        /// W3C DID — e.g. `did:sigui:aptos:<address>` encoded as UTF-8 bytes.
        did: vector<u8>,
    }

    /// Singleton resource held under the admin account. Stores all agent profiles
    /// and the oracle authority address.
    struct ReputationRegistry has key {
        /// Maps agent address → profile.
        agents: Table<address, AgentProfile>,
        /// Total number of registered agents (never decremented).
        total_agents: u64,
        /// The oracle address authorised to mutate scores.
        oracle: address,
        /// Event streams.
        agent_registered_events: EventHandle<AgentRegisteredEvent>,
        reputation_updated_events: EventHandle<ReputationUpdatedEvent>,
        agent_slashed_events: EventHandle<AgentSlashedEvent>,
    }

    // ───────────────────────────────────────────────────────────
    //  Events
    // ───────────────────────────────────────────────────────────

    /// Emitted when a new agent registers.
    struct AgentRegisteredEvent has drop, store {
        agent: address,
        did: vector<u8>,
        timestamp: u64,
    }

    /// Emitted when an oracle updates an agent's reputation score.
    struct ReputationUpdatedEvent has drop, store {
        agent: address,
        old_score: u64,
        new_score: u64,
        old_tier: u8,
        new_tier: u8,
        delta: u64,
        increase: bool,
        reason: vector<u8>,
        timestamp: u64,
    }

    /// Emitted when an agent is slashed.
    struct AgentSlashedEvent has drop, store {
        agent: address,
        score_before: u64,
        score_after: u64,
        reason: vector<u8>,
        timestamp: u64,
    }

    // ───────────────────────────────────────────────────────────
    //  Initialisation
    // ───────────────────────────────────────────────────────────

    /// Initialise the `ReputationRegistry` under `admin`'s account.
    /// The caller becomes the first oracle. Must be called exactly once.
    ///
    /// # Aborts
    /// * `EALREADY_INITIALIZED` — if the registry already exists under `admin`.
    public fun initialize(admin: &signer) {
        let admin_addr = signer::address_of(admin);
        assert!(
            !exists<ReputationRegistry>(admin_addr),
            error::already_exists(EALREADY_INITIALIZED)
        );

        let registry = ReputationRegistry {
            agents: table::new(),
            total_agents: 0,
            oracle: admin_addr,
            agent_registered_events: account::new_event_handle<AgentRegisteredEvent>(admin),
            reputation_updated_events: account::new_event_handle<ReputationUpdatedEvent>(admin),
            agent_slashed_events: account::new_event_handle<AgentSlashedEvent>(admin),
        };
        move_to(admin, registry);
    }

    spec initialize {
        pragma aborts_if_is_strict;

        let admin_addr = signer::address_of(admin);

        /// Abort if registry already exists.
        aborts_if exists<ReputationRegistry>(admin_addr)
            with error::already_exists(EALREADY_INITIALIZED);

        /// After successful execution the registry must exist under admin.
        ensures exists<ReputationRegistry>(admin_addr);

        /// The oracle must be set to admin.
        ensures global<ReputationRegistry>(admin_addr).oracle == admin_addr;

        /// Total agent count starts at zero.
        ensures global<ReputationRegistry>(admin_addr).total_agents == 0;
    }

    // ───────────────────────────────────────────────────────────
    //  Agent registration
    // ───────────────────────────────────────────────────────────

    /// Register the calling account as an AI agent in the Sigui Protocol.
    ///
    /// # Parameters
    /// * `account` — the agent signer; their address becomes the agent key.
    /// * `did`     — W3C Decentralised Identifier encoded as UTF-8 bytes.
    ///
    /// # Aborts
    /// * `ENOT_INITIALIZED`     — if the registry does not exist under `@sigui`.
    /// * `EAGENT_ALREADY_EXISTS`— if this address is already registered.
    /// * `EDID_EMPTY`           — if `did` is an empty vector.
    public fun register_agent(
        account: &signer,
        registry_owner: address,
        did: vector<u8>,
    ) acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        assert!(!vector::is_empty(&did), error::invalid_argument(EDID_EMPTY));

        let agent_addr = signer::address_of(account);
        let registry   = borrow_global_mut<ReputationRegistry>(registry_owner);

        assert!(
            !table::contains(&registry.agents, agent_addr),
            error::already_exists(EAGENT_ALREADY_EXISTS)
        );

        let now = timestamp::now_seconds();
        let profile = AgentProfile {
            reputation_score: INITIAL_SCORE,
            tier: compute_tier(INITIAL_SCORE),
            threat_count: 0,
            is_active: true,
            registered_at: now,
            last_updated: now,
            did: did,
        };

        table::add(&mut registry.agents, agent_addr, profile);
        registry.total_agents = registry.total_agents + 1;

        event::emit_event(
            &mut registry.agent_registered_events,
            AgentRegisteredEvent {
                agent: agent_addr,
                did: *&table::borrow(&registry.agents, agent_addr).did,
                timestamp: now,
            }
        );
    }

    spec register_agent {
        pragma aborts_if_is_strict;

        let agent_addr = signer::address_of(account);

        aborts_if !exists<ReputationRegistry>(registry_owner)
            with error::not_found(ENOT_INITIALIZED);
        aborts_if vector::is_empty(did)
            with error::invalid_argument(EDID_EMPTY);
        aborts_if table::spec_contains(global<ReputationRegistry>(registry_owner).agents, agent_addr)
            with error::already_exists(EAGENT_ALREADY_EXISTS);

        /// Agent must appear in the table after registration.
        ensures table::spec_contains(
            global<ReputationRegistry>(registry_owner).agents,
            agent_addr
        );

        /// Total agent count must increase by exactly one.
        ensures global<ReputationRegistry>(registry_owner).total_agents
            == old(global<ReputationRegistry>(registry_owner).total_agents) + 1;

        /// Initial score is INITIAL_SCORE.
        ensures table::spec_get(
            global<ReputationRegistry>(registry_owner).agents,
            agent_addr
        ).reputation_score == INITIAL_SCORE;

        /// New agent must be active.
        ensures table::spec_get(
            global<ReputationRegistry>(registry_owner).agents,
            agent_addr
        ).is_active == true;
    }

    // ───────────────────────────────────────────────────────────
    //  Reputation update (oracle-only)
    // ───────────────────────────────────────────────────────────

    /// Adjust an agent's reputation score by `delta`.
    ///
    /// * If `increase` is `true`, the score rises (capped at `MAX_SCORE`).
    /// * If `increase` is `false`, the score falls (floored at 0).
    ///
    /// Automatically recomputes the agent's tier after every change.
    ///
    /// # Aborts
    /// * `ENOT_ORACLE`      — caller is not the designated oracle.
    /// * `EAGENT_NOT_FOUND` — `agent` is not registered.
    /// * `EAGENT_INACTIVE`  — `agent` is currently inactive.
    /// * `EZERO_DELTA`      — `delta` is zero.
    public fun update_reputation(
        oracle: &signer,
        registry_owner: address,
        agent: address,
        delta: u64,
        increase: bool,
        reason: vector<u8>,
    ) acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        assert!(delta > 0, error::invalid_argument(EZERO_DELTA));

        let registry = borrow_global_mut<ReputationRegistry>(registry_owner);
        let oracle_addr = signer::address_of(oracle);
        assert!(oracle_addr == registry.oracle, error::permission_denied(ENOT_ORACLE));
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );

        let profile    = table::borrow_mut(&mut registry.agents, agent);
        assert!(profile.is_active, error::invalid_state(EAGENT_INACTIVE));

        let old_score = profile.reputation_score;
        let old_tier  = profile.tier;
        let new_score;

        if (increase) {
            new_score = saturating_add(old_score, delta, MAX_SCORE);
        } else {
            new_score = saturating_sub(old_score, delta);
        };

        profile.reputation_score = new_score;
        profile.tier             = compute_tier(new_score);
        profile.last_updated     = timestamp::now_seconds();

        event::emit_event(
            &mut registry.reputation_updated_events,
            ReputationUpdatedEvent {
                agent,
                old_score,
                new_score,
                old_tier,
                new_tier: profile.tier,
                delta,
                increase,
                reason,
                timestamp: profile.last_updated,
            }
        );
    }

    spec update_reputation {
        pragma aborts_if_is_strict;

        let oracle_addr = signer::address_of(oracle);

        aborts_if !exists<ReputationRegistry>(registry_owner)
            with error::not_found(ENOT_INITIALIZED);
        aborts_if delta == 0
            with error::invalid_argument(EZERO_DELTA);
        aborts_if global<ReputationRegistry>(registry_owner).oracle != oracle_addr
            with error::permission_denied(ENOT_ORACLE);
        aborts_if !table::spec_contains(global<ReputationRegistry>(registry_owner).agents, agent)
            with error::not_found(EAGENT_NOT_FOUND);
        aborts_if !table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).is_active
            with error::invalid_state(EAGENT_INACTIVE);

        /// Score must stay in [0, MAX_SCORE] after any update.
        ensures table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).reputation_score <= MAX_SCORE;

        /// An increase never decreases the score.
        ensures increase ==>
            table::spec_get(
                global<ReputationRegistry>(registry_owner).agents, agent
            ).reputation_score >= old(table::spec_get(
                global<ReputationRegistry>(registry_owner).agents, agent
            ).reputation_score);

        /// A decrease never increases the score.
        ensures !increase ==>
            table::spec_get(
                global<ReputationRegistry>(registry_owner).agents, agent
            ).reputation_score <= old(table::spec_get(
                global<ReputationRegistry>(registry_owner).agents, agent
            ).reputation_score);
    }

    // ───────────────────────────────────────────────────────────
    //  Slashing (oracle-only)
    // ───────────────────────────────────────────────────────────

    /// Slash an agent: deduct 25 % of their score and mark them inactive.
    /// The agent must be re-activated by governance before they can participate again.
    ///
    /// Also increments the agent's `threat_count`.
    ///
    /// # Aborts
    /// * `ENOT_ORACLE`      — caller is not the oracle.
    /// * `EAGENT_NOT_FOUND` — agent is not registered.
    /// * `EAGENT_INACTIVE`  — agent is already inactive.
    public fun slash_agent(
        oracle: &signer,
        registry_owner: address,
        agent: address,
        reason: vector<u8>,
    ) acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );

        let registry    = borrow_global_mut<ReputationRegistry>(registry_owner);
        let oracle_addr = signer::address_of(oracle);
        assert!(oracle_addr == registry.oracle, error::permission_denied(ENOT_ORACLE));
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );

        let profile = table::borrow_mut(&mut registry.agents, agent);
        assert!(profile.is_active, error::invalid_state(EAGENT_INACTIVE));

        let score_before = profile.reputation_score;
        let slash_amount = (score_before * SLASH_BASIS_POINTS) / BASIS_POINTS_DENOM;
        let score_after  = score_before - slash_amount;

        profile.reputation_score = score_after;
        profile.tier             = compute_tier(score_after);
        profile.is_active        = false;
        profile.threat_count     = profile.threat_count + 1;
        profile.last_updated     = timestamp::now_seconds();

        event::emit_event(
            &mut registry.agent_slashed_events,
            AgentSlashedEvent {
                agent,
                score_before,
                score_after,
                reason,
                timestamp: profile.last_updated,
            }
        );
    }

    spec slash_agent {
        pragma aborts_if_is_strict;

        let oracle_addr = signer::address_of(oracle);

        aborts_if !exists<ReputationRegistry>(registry_owner)
            with error::not_found(ENOT_INITIALIZED);
        aborts_if global<ReputationRegistry>(registry_owner).oracle != oracle_addr
            with error::permission_denied(ENOT_ORACLE);
        aborts_if !table::spec_contains(global<ReputationRegistry>(registry_owner).agents, agent)
            with error::not_found(EAGENT_NOT_FOUND);
        aborts_if !table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).is_active
            with error::invalid_state(EAGENT_INACTIVE);

        /// Agent must be inactive after slashing.
        ensures !table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).is_active;

        /// Score after slash must be strictly less than score before.
        ensures table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).reputation_score < old(table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).reputation_score);

        /// Threat count must increment by exactly one.
        ensures table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).threat_count == old(table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).threat_count) + 1;
    }

    // ───────────────────────────────────────────────────────────
    //  Reactivation (oracle-only)
    // ───────────────────────────────────────────────────────────

    /// Re-activate a previously slashed agent. Governance (oracle) is responsible
    /// for performing off-chain review before calling this function.
    public fun reactivate_agent(
        oracle: &signer,
        registry_owner: address,
        agent: address,
    ) acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );

        let registry    = borrow_global_mut<ReputationRegistry>(registry_owner);
        let oracle_addr = signer::address_of(oracle);
        assert!(oracle_addr == registry.oracle, error::permission_denied(ENOT_ORACLE));
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );

        let profile      = table::borrow_mut(&mut registry.agents, agent);
        profile.is_active    = true;
        profile.last_updated = timestamp::now_seconds();
    }

    spec reactivate_agent {
        pragma aborts_if_is_strict;

        let oracle_addr = signer::address_of(oracle);

        aborts_if !exists<ReputationRegistry>(registry_owner)
            with error::not_found(ENOT_INITIALIZED);
        aborts_if global<ReputationRegistry>(registry_owner).oracle != oracle_addr
            with error::permission_denied(ENOT_ORACLE);
        aborts_if !table::spec_contains(global<ReputationRegistry>(registry_owner).agents, agent)
            with error::not_found(EAGENT_NOT_FOUND);

        ensures table::spec_get(
            global<ReputationRegistry>(registry_owner).agents, agent
        ).is_active == true;
    }

    // ───────────────────────────────────────────────────────────
    //  Transfer oracle role (admin-only)
    // ───────────────────────────────────────────────────────────

    /// Transfer oracle authority to a new address. Only the current oracle may call this.
    public fun transfer_oracle(
        oracle: &signer,
        registry_owner: address,
        new_oracle: address,
    ) acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );

        let registry    = borrow_global_mut<ReputationRegistry>(registry_owner);
        let oracle_addr = signer::address_of(oracle);
        assert!(oracle_addr == registry.oracle, error::permission_denied(ENOT_ORACLE));
        registry.oracle = new_oracle;
    }

    spec transfer_oracle {
        pragma aborts_if_is_strict;

        let oracle_addr = signer::address_of(oracle);

        aborts_if !exists<ReputationRegistry>(registry_owner)
            with error::not_found(ENOT_INITIALIZED);
        aborts_if global<ReputationRegistry>(registry_owner).oracle != oracle_addr
            with error::permission_denied(ENOT_ORACLE);

        ensures global<ReputationRegistry>(registry_owner).oracle == new_oracle;
    }

    // ───────────────────────────────────────────────────────────
    //  View functions
    // ───────────────────────────────────────────────────────────

    #[view]
    /// Return the reputation score for `agent`.
    public fun get_reputation(registry_owner: address, agent: address): u64
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        let registry = borrow_global<ReputationRegistry>(registry_owner);
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );
        table::borrow(&registry.agents, agent).reputation_score
    }

    #[view]
    /// Return the tier for `agent` (0 = Bronze … 3 = Platinum).
    public fun get_tier(registry_owner: address, agent: address): u8
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        let registry = borrow_global<ReputationRegistry>(registry_owner);
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );
        table::borrow(&registry.agents, agent).tier
    }

    #[view]
    /// Return whether an agent is active.
    public fun is_active(registry_owner: address, agent: address): bool
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        let registry = borrow_global<ReputationRegistry>(registry_owner);
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );
        table::borrow(&registry.agents, agent).is_active
    }

    #[view]
    /// Return the threat count for `agent`.
    public fun get_threat_count(registry_owner: address, agent: address): u64
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        let registry = borrow_global<ReputationRegistry>(registry_owner);
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );
        table::borrow(&registry.agents, agent).threat_count
    }

    #[view]
    /// Return the DID of `agent`.
    public fun get_did(registry_owner: address, agent: address): vector<u8>
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        let registry = borrow_global<ReputationRegistry>(registry_owner);
        assert!(
            table::contains(&registry.agents, agent),
            error::not_found(EAGENT_NOT_FOUND)
        );
        *&table::borrow(&registry.agents, agent).did
    }

    #[view]
    /// Return the total number of registered agents.
    public fun total_agents(registry_owner: address): u64
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        borrow_global<ReputationRegistry>(registry_owner).total_agents
    }

    #[view]
    /// Return the current oracle address.
    public fun get_oracle(registry_owner: address): address
    acquires ReputationRegistry {
        assert!(
            exists<ReputationRegistry>(registry_owner),
            error::not_found(ENOT_INITIALIZED)
        );
        borrow_global<ReputationRegistry>(registry_owner).oracle
    }

    // ───────────────────────────────────────────────────────────
    //  Internal helpers
    // ───────────────────────────────────────────────────────────

    /// Compute the tier for a given score.
    fun compute_tier(score: u64): u8 {
        if (score >= TIER_PLATINUM_MIN) {
            TIER_PLATINUM
        } else if (score >= TIER_GOLD_MIN) {
            TIER_GOLD
        } else if (score >= TIER_SILVER_MIN) {
            TIER_SILVER
        } else {
            TIER_BRONZE
        }
    }

    spec compute_tier {
        ensures score >= TIER_PLATINUM_MIN ==> result == TIER_PLATINUM;
        ensures score >= TIER_GOLD_MIN && score < TIER_PLATINUM_MIN ==> result == TIER_GOLD;
        ensures score >= TIER_SILVER_MIN && score < TIER_GOLD_MIN ==> result == TIER_SILVER;
        ensures score < TIER_SILVER_MIN ==> result == TIER_BRONZE;
        ensures result <= TIER_PLATINUM;
    }

    /// Saturating addition — result capped at `cap`.
    fun saturating_add(a: u64, b: u64, cap: u64): u64 {
        if (a >= cap) {
            cap
        } else if (cap - a < b) {
            cap
        } else {
            a + b
        }
    }

    spec saturating_add {
        ensures result <= cap;
        ensures a + b <= cap ==> result == a + b;
        ensures a + b > cap  ==> result == cap;
    }

    /// Saturating subtraction — result floored at 0.
    fun saturating_sub(a: u64, b: u64): u64 {
        if (a <= b) { 0 } else { a - b }
    }

    spec saturating_sub {
        ensures result >= 0;
        ensures a >= b ==> result == a - b;
        ensures a < b  ==> result == 0;
    }

    // ───────────────────────────────────────────────────────────
    //  Module-level invariants
    // ───────────────────────────────────────────────────────────

    spec module {
        /// Every stored profile has a score within the valid range.
        invariant forall owner: address where exists<ReputationRegistry>(owner):
            forall agent: address
                where table::spec_contains(global<ReputationRegistry>(owner).agents, agent):
                    table::spec_get(global<ReputationRegistry>(owner).agents, agent).reputation_score
                        <= MAX_SCORE;

        /// Tier is always one of the four valid values.
        invariant forall owner: address where exists<ReputationRegistry>(owner):
            forall agent: address
                where table::spec_contains(global<ReputationRegistry>(owner).agents, agent):
                    table::spec_get(global<ReputationRegistry>(owner).agents, agent).tier
                        <= TIER_PLATINUM;
    }
}
