module sigui::threat_registry {
    use std::signer;
    use std::vector;
    use aptos_framework::timestamp;
    use aptos_std::table::{Self, Table};

    /// Errors
    const ENOT_AUTHORIZED: u64 = 1;
    const ETHREAT_NOT_FOUND: u64 = 2;
    const EALREADY_VALIDATED: u64 = 3;

    struct ThreatPattern has store, drop, copy {
        id: u64,
        severity: u8,
        pattern_hash: vector<u8>,
        reporter: address,
        validated: bool,
        timestamp: u64,
        validator_count: u64
    }

    struct ThreatRegistry has key {
        threats: Table<u64, ThreatPattern>,
        threat_count: u64,
        oracles: vector<address>
    }

    #[event]
    struct ThreatReportedEvent has drop, store {
        id: u64,
        reporter: address,
        severity: u8,
        pattern_hash: vector<u8>
    }

    #[event]
    struct ThreatValidatedEvent has drop, store {
        id: u64,
        validator: address,
        completely_validated: bool
    }

    public fun initialize(admin: &signer) {
        let admin_addr = signer::address_of(admin);
        if (!exists<ThreatRegistry>(admin_addr)) {
            let oracles = vector::empty<address>();
            vector::push_back(&mut oracles, admin_addr);
            
            move_to(admin, ThreatRegistry {
                threats: table::new(),
                threat_count: 0,
                oracles
            });
        }
    }

    public fun add_oracle(admin: &signer, registry_addr: address, new_oracle: address) acquires ThreatRegistry {
        assert!(signer::address_of(admin) == registry_addr, ENOT_AUTHORIZED);
        let registry = borrow_global_mut<ThreatRegistry>(registry_addr);
        if (!vector::contains(&registry.oracles, &new_oracle)) {
            vector::push_back(&mut registry.oracles, new_oracle);
        }
    }

    public fun report_threat(
        reporter: &signer,
        registry_addr: address,
        severity: u8,
        pattern_hash: vector<u8>
    ): u64 acquires ThreatRegistry {
        let reporter_addr = signer::address_of(reporter);
        let registry = borrow_global_mut<ThreatRegistry>(registry_addr);
        
        let id = registry.threat_count + 1;
        
        let threat = ThreatPattern {
            id,
            severity,
            pattern_hash: copy pattern_hash,
            reporter: reporter_addr,
            validated: false,
            timestamp: timestamp::now_seconds(),
            validator_count: 0
        };
        
        table::add(&mut registry.threats, id, threat);
        registry.threat_count = id;
        
        0x1::event::emit(ThreatReportedEvent {
            id,
            reporter: reporter_addr,
            severity,
            pattern_hash
        });
        
        id
    }

    public fun validate_threat(
        oracle: &signer,
        registry_addr: address,
        threat_id: u64
    ) acquires ThreatRegistry {
        let oracle_addr = signer::address_of(oracle);
        let registry = borrow_global_mut<ThreatRegistry>(registry_addr);
        
        assert!(vector::contains(&registry.oracles, &oracle_addr), ENOT_AUTHORIZED);
        assert!(table::contains(&registry.threats, threat_id), ETHREAT_NOT_FOUND);
        
        let threat = table::borrow_mut(&mut registry.threats, threat_id);
        assert!(!threat.validated, EALREADY_VALIDATED);
        
        threat.validator_count = threat.validator_count + 1;
        
        // Require 2 signatures
        if (threat.validator_count >= 2) {
            threat.validated = true;
        }
        
        0x1::event::emit(ThreatValidatedEvent {
            id: threat_id,
            validator: oracle_addr,
            completely_validated: threat.validated
        });
    }

    #[view]
    public fun get_threat_count(registry_addr: address): u64 acquires ThreatRegistry {
        borrow_global<ThreatRegistry>(registry_addr).threat_count
    }

    #[view]
    public fun is_threat_validated(registry_addr: address, threat_id: u64): bool acquires ThreatRegistry {
        if (!table::contains(&borrow_global<ThreatRegistry>(registry_addr).threats, threat_id)) {
            return false
        };
        table::borrow(&borrow_global<ThreatRegistry>(registry_addr).threats, threat_id).validated
    }

    // --- Formal Verification Specs (Move Prover) ---
    spec report_threat {
        aborts_if !exists<ThreatRegistry>(registry_addr);
        ensures global<ThreatRegistry>(registry_addr).threat_count == old(global<ThreatRegistry>(registry_addr).threat_count) + 1;
    }

    spec validate_threat {
        aborts_if !exists<ThreatRegistry>(registry_addr);
        let registry = global<ThreatRegistry>(registry_addr);
        aborts_if !vector::contains(registry.oracles, signer::address_of(oracle));
        aborts_if !table::contains(registry.threats, threat_id);
    }
}
