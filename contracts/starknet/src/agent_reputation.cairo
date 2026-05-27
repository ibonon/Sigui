// ============================================================
//  Sigui Protocol — AgentReputation Contract
//  SPDX-License-Identifier: MIT
//
//  Implements ERC-8259 compatible decentralised AI agent
//  identity scoring. Agents accumulate a u64 reputation score
//  through oracle-attested interactions. Tiers are derived
//  on-chain from score thresholds; slashing is irreversible
//  within the same tier window.
//
//  Access roles
//  ─────────────
//  OWNER   : can grant/revoke ORACLE role, pause contract
//  ORACLE  : can call update_reputation / slash_agent
//
//  Tier thresholds (representative defaults)
//  ─────────────────────────────────────────
//   0  → TIER_NOVICE     (score  0 – 999)
//   1  → TIER_RELIABLE   (score  1 000 – 9 999)
//   2  → TIER_TRUSTED    (score 10 000 – 99 999)
//   3  → TIER_ELITE      (score ≥ 100 000)
// ============================================================

// ── External imports ─────────────────────────────────────────
use starknet::{ContractAddress, get_caller_address, get_block_timestamp};
use openzeppelin_access::ownable::OwnableComponent;
use openzeppelin_security::pausable::PausableComponent;

// ── Public interface ──────────────────────────────────────────

/// Public ABI exposed by AgentReputation.
#[starknet::interface]
pub trait IAgentReputation<TContractState> {
    // ── Write ─────────────────────────────────────────────────

    /// Register the caller as a new agent with a Decentralised
    /// Identifier string (`did`).  Reverts if already registered.
    fn register_agent(ref self: TContractState, did: ByteArray);

    /// Apply a signed `delta` to an agent's reputation score.
    /// Only callable by an account that holds the ORACLE role.
    ///
    /// * `agent`  – target agent address
    /// * `delta`  – signed change (positive = reward, negative = penalty)
    /// * `reason` – human-readable audit string stored as an event field
    fn update_reputation(
        ref self: TContractState,
        agent: ContractAddress,
        delta: i64,
        reason: ByteArray,
    );

    /// Immediately zero-out an agent's score and mark them as
    /// slashed.  Increments `threat_count` on the profile.
    /// Only callable by ORACLE role.
    fn slash_agent(ref self: TContractState, agent: ContractAddress, reason: ByteArray);

    /// Grant the ORACLE role to `account`.  Owner only.
    fn grant_oracle(ref self: TContractState, account: ContractAddress);

    /// Revoke the ORACLE role from `account`.  Owner only.
    fn revoke_oracle(ref self: TContractState, account: ContractAddress);

    /// Pause all state-changing operations.  Owner only.
    fn pause(ref self: TContractState);

    /// Resume state-changing operations.  Owner only.
    fn unpause(ref self: TContractState);

    // ── Read ──────────────────────────────────────────────────

    /// Return the raw reputation score for `agent`.
    fn get_reputation(self: @TContractState, agent: ContractAddress) -> u64;

    /// Return the full `AgentProfile` struct for `agent`.
    fn get_profile(self: @TContractState, agent: ContractAddress) -> AgentProfile;

    /// Return `true` if `account` holds the ORACLE role.
    fn is_oracle(self: @TContractState, account: ContractAddress) -> bool;

    /// Return the contract owner address.
    fn owner(self: @TContractState) -> ContractAddress;

    /// Return `true` if the contract is paused.
    fn is_paused(self: @TContractState) -> bool;
}

// ── Data structures ───────────────────────────────────────────

/// Complete on-chain profile for a registered AI agent.
#[derive(Drop, Serde, Copy, starknet::Store)]
pub struct AgentProfile {
    /// Cumulative reputation score (saturates at u64::MAX).
    pub reputation_score: u64,
    /// Derived tier badge: 0=Novice, 1=Reliable, 2=Trusted, 3=Elite.
    pub tier: u8,
    /// Total number of slash events applied to this agent.
    pub threat_count: u64,
    /// `false` after a terminal slash that disables the agent.
    pub is_active: bool,
    /// Block timestamp at first registration (immutable).
    pub registered_at: u64,
    /// Block timestamp of the most recent reputation mutation.
    pub last_updated: u64,
}

// ── Contract ──────────────────────────────────────────────────

/// Sigui AgentReputation — on-chain identity scoring for AI agents.
#[starknet::contract]
pub mod AgentReputation {
    use super::{
        IAgentReputation, AgentProfile,
        OwnableComponent, PausableComponent
    };

    // ── Component wiring ──────────────────────────────────────────
    component!(path: OwnableComponent, storage: ownable, event: OwnableEvent);
    component!(path: PausableComponent, storage: pausable, event: PausableEvent);

    // Ownable internal helpers (owner check + transfer)
    #[abi(embed_v0)]
    impl OwnableMixinImpl = OwnableComponent::OwnableTwoStepMixinImpl<ContractState>;
    impl OwnableInternalImpl = OwnableComponent::InternalImpl<ContractState>;

    // Pausable internal helpers
    #[abi(embed_v0)]
    impl PausableMixinImpl = PausableComponent::PausableImpl<ContractState>;
    impl PausableInternalImpl = PausableComponent::InternalImpl<ContractState>;
    use starknet::{ContractAddress, get_caller_address, get_block_timestamp};
    use starknet::storage::{Map, StoragePointerReadAccess, StoragePointerWriteAccess, StorageMapReadAccess, StorageMapWriteAccess};

    // ── Tier thresholds ───────────────────────────────────────
    const TIER_RELIABLE_MIN: u64 = 1_000_u64;
    const TIER_TRUSTED_MIN:  u64 = 10_000_u64;
    const TIER_ELITE_MIN:    u64 = 100_000_u64;

    /// Score granted on successful registration.
    const GENESIS_SCORE: u64 = 100_u64;

    // ── Storage ───────────────────────────────────────────────
    #[storage]
    struct Storage {
        /// Component sub-storage for Ownable.
        #[substorage(v0)]
        ownable: OwnableComponent::Storage,
        /// Component sub-storage for Pausable.
        #[substorage(v0)]
        pausable: PausableComponent::Storage,
        /// agent address → full profile.
        profiles: Map<ContractAddress, AgentProfile>,
        /// agent address → DID string hash (keccak of the ByteArray).
        did_hashes: Map<ContractAddress, felt252>,
        /// account address → oracle role flag.
        oracles: Map<ContractAddress, bool>,
        /// agent address → registration flag (avoids re-registration).
        registered: Map<ContractAddress, bool>,
    }

    // ── Events ────────────────────────────────────────────────
    #[event]
    #[derive(Drop, starknet::Event)]
    pub enum Event {
        #[flat]
        OwnableEvent: OwnableComponent::Event,
        #[flat]
        PausableEvent: PausableComponent::Event,
        AgentRegistered: AgentRegistered,
        ReputationUpdated: ReputationUpdated,
        AgentSlashed: AgentSlashed,
        OracleGranted: OracleGranted,
        OracleRevoked: OracleRevoked,
    }

    /// Emitted the first time an agent registers on-chain.
    #[derive(Drop, starknet::Event)]
    pub struct AgentRegistered {
        /// Indexed so off-chain indexers can filter by agent.
        #[key]
        pub agent: ContractAddress,
        /// DID string supplied at registration time.
        pub did: ByteArray,
        /// Block timestamp of registration.
        pub timestamp: u64,
    }

    /// Emitted every time an oracle mutates a score.
    #[derive(Drop, starknet::Event)]
    pub struct ReputationUpdated {
        #[key]
        pub agent: ContractAddress,
        /// Score value *before* this update.
        pub previous_score: u64,
        /// Score value *after* this update.
        pub new_score: u64,
        /// Signed delta applied (positive or negative).
        pub delta: i64,
        /// Human-readable reason provided by the oracle.
        pub reason: ByteArray,
        /// Oracle address that triggered this event.
        pub oracle: ContractAddress,
        pub timestamp: u64,
    }

    /// Emitted when an oracle slashes an agent.
    #[derive(Drop, starknet::Event)]
    pub struct AgentSlashed {
        #[key]
        pub agent: ContractAddress,
        pub reason: ByteArray,
        pub oracle: ContractAddress,
        pub threat_count: u64,
        pub timestamp: u64,
    }

    /// Emitted when a new oracle role is granted.
    #[derive(Drop, starknet::Event)]
    pub struct OracleGranted {
        #[key]
        pub account: ContractAddress,
        pub by_owner: ContractAddress,
    }

    /// Emitted when an oracle role is revoked.
    #[derive(Drop, starknet::Event)]
    pub struct OracleRevoked {
        #[key]
        pub account: ContractAddress,
        pub by_owner: ContractAddress,
    }

    // ── Constructor ───────────────────────────────────────────

    /// Deploy the contract, setting `owner` as the initial owner
    /// and optionally granting the oracle role to `initial_oracle`
    /// (pass zero address to skip).
    #[constructor]
    fn constructor(
        ref self: ContractState,
        owner: ContractAddress,
        initial_oracle: ContractAddress,
    ) {
        // Initialize Ownable with the provided owner address.
        self.ownable.initializer(owner);

        // Grant oracle role to initial_oracle if non-zero.
        let zero: ContractAddress = starknet::contract_address_const::<0>();
        if initial_oracle != zero {
            self.oracles.write(initial_oracle, true);
        }
    }

    // ── Internal helpers ──────────────────────────────────────
    #[generate_trait]
    impl InternalImpl of InternalTrait {
        /// Revert if caller does not hold ORACLE role.
        fn assert_oracle(self: @ContractState) {
            let caller = get_caller_address();
            assert(self.oracles.read(caller), 'SIGUI: caller not oracle');
        }

        /// Revert if `agent` is not registered.
        fn assert_registered(self: @ContractState, agent: ContractAddress) {
            assert(self.registered.read(agent), 'SIGUI: agent not registered');
        }

        /// Derive the tier badge from a raw reputation score.
        fn score_to_tier(score: u64) -> u8 {
            if score >= TIER_ELITE_MIN {
                3_u8
            } else if score >= TIER_TRUSTED_MIN {
                2_u8
            } else if score >= TIER_RELIABLE_MIN {
                1_u8
            } else {
                0_u8
            }
        }

        /// Apply `delta` to `base`, clamping to [0, u64::MAX].
        fn apply_delta(base: u64, delta: i64) -> u64 {
            if delta >= 0_i64 {
                // Saturating add: cap at u64::MAX.
                let d: u64 = delta.try_into().unwrap();
                base.saturating_add(d)
            } else {
                // Saturating sub: floor at 0.
                let d: u64 = (-delta).try_into().unwrap();
                if d >= base {
                    0_u64
                } else {
                    base - d
                }
            }
        }
    }

    // ── External implementation ───────────────────────────────
    #[abi(embed_v0)]
    impl AgentReputationImpl of IAgentReputation<ContractState> {

        // ── Write functions ───────────────────────────────────

        fn register_agent(ref self: ContractState, did: ByteArray) {
            self.pausable.assert_not_paused();
            let caller = get_caller_address();
            assert(!self.registered.read(caller), 'SIGUI: already registered');

            let now = get_block_timestamp();

            // Create genesis profile.
            let profile = AgentProfile {
                reputation_score: GENESIS_SCORE,
                tier: InternalImpl::score_to_tier(GENESIS_SCORE),
                threat_count: 0_u64,
                is_active: true,
                registered_at: now,
                last_updated: now,
            };

            self.profiles.write(caller, profile);
            self.registered.write(caller, true);

            self.emit(AgentRegistered { agent: caller, did, timestamp: now });
        }

        fn update_reputation(
            ref self: ContractState,
            agent: ContractAddress,
            delta: i64,
            reason: ByteArray,
        ) {
            self.pausable.assert_not_paused();
            self.assert_oracle();
            self.assert_registered(agent);

            let oracle = get_caller_address();
            let now = get_block_timestamp();

            let mut profile = self.profiles.read(agent);
            assert(profile.is_active, 'SIGUI: agent is inactive');

            let previous_score = profile.reputation_score;
            let new_score = InternalImpl::apply_delta(previous_score, delta);

            profile.reputation_score = new_score;
            profile.tier = InternalImpl::score_to_tier(new_score);
            profile.last_updated = now;

            self.profiles.write(agent, profile);

            self.emit(ReputationUpdated {
                agent,
                previous_score,
                new_score,
                delta,
                reason,
                oracle,
                timestamp: now,
            });
        }

        fn slash_agent(ref self: ContractState, agent: ContractAddress, reason: ByteArray) {
            self.pausable.assert_not_paused();
            self.assert_oracle();
            self.assert_registered(agent);

            let oracle = get_caller_address();
            let now = get_block_timestamp();

            let mut profile = self.profiles.read(agent);

            // Zero the score, increment threat count, deactivate.
            profile.reputation_score = 0_u64;
            profile.tier = 0_u8;
            profile.threat_count += 1_u64;
            profile.is_active = false;
            profile.last_updated = now;

            self.profiles.write(agent, profile);

            self.emit(AgentSlashed {
                agent,
                reason,
                oracle,
                threat_count: profile.threat_count,
                timestamp: now,
            });
        }

        fn grant_oracle(ref self: ContractState, account: ContractAddress) {
            self.ownable.assert_only_owner();
            self.oracles.write(account, true);
            self.emit(OracleGranted { account, by_owner: get_caller_address() });
        }

        fn revoke_oracle(ref self: ContractState, account: ContractAddress) {
            self.ownable.assert_only_owner();
            self.oracles.write(account, false);
            self.emit(OracleRevoked { account, by_owner: get_caller_address() });
        }

        fn pause(ref self: ContractState) {
            self.ownable.assert_only_owner();
            self.pausable.pause();
        }

        fn unpause(ref self: ContractState) {
            self.ownable.assert_only_owner();
            self.pausable.unpause();
        }

        // ── Read functions ────────────────────────────────────

        fn get_reputation(self: @ContractState, agent: ContractAddress) -> u64 {
            self.profiles.read(agent).reputation_score
        }

        fn get_profile(self: @ContractState, agent: ContractAddress) -> AgentProfile {
            self.profiles.read(agent)
        }

        fn is_oracle(self: @ContractState, account: ContractAddress) -> bool {
            self.oracles.read(account)
        }

        fn owner(self: @ContractState) -> ContractAddress {
            self.ownable.owner()
        }

        fn is_paused(self: @ContractState) -> bool {
            self.pausable.is_paused()
        }
    }
}
