use starknet::ContractAddress;

#[starknet::interface]
pub trait IThreatRegistry<TContractState> {
    fn report_threat(
        ref self: TContractState,
        severity: u8,
        pattern_hash: felt252,
    ) -> u256;
    fn validate_threat(ref self: TContractState, threat_id: u256);
    fn get_threat(self: @TContractState, threat_id: u256) -> ThreatPattern;
    fn get_threat_count(self: @TContractState) -> u256;
    fn add_oracle(ref self: TContractState, oracle: ContractAddress);
    fn remove_oracle(ref self: TContractState, oracle: ContractAddress);
}

#[derive(Drop, Serde, starknet::Store)]
pub struct ThreatPattern {
    pub id: u256,
    pub severity: u8,
    pub pattern_hash: felt252,
    pub reporter: ContractAddress,
    pub validator_count: u64,
    pub validated: bool,
    pub timestamp: u64,
}

#[starknet::contract]
pub mod ThreatRegistry {
    use starknet::{ContractAddress, get_caller_address, get_block_timestamp};
    use super::{IThreatRegistry, ThreatPattern};
    use starknet::storage::{
        Map, StorageMapReadAccess, StorageMapWriteAccess,
        StoragePointerReadAccess, StoragePointerWriteAccess
    };

    #[storage]
    struct Storage {
        threats: Map<u256, ThreatPattern>,
        threat_count: u256,
        oracles: Map<ContractAddress, bool>,
        threat_validations: Map<(u256, ContractAddress), bool>,
        owner: ContractAddress,
    }

    #[event]
    #[derive(Drop, starknet::Event)]
    pub enum Event {
        ThreatReported: ThreatReported,
        ThreatValidated: ThreatValidated,
    }

    #[derive(Drop, starknet::Event)]
    pub struct ThreatReported {
        pub id: u256,
        pub reporter: ContractAddress,
        pub severity: u8,
        pub pattern_hash: felt252,
    }

    #[derive(Drop, starknet::Event)]
    pub struct ThreatValidated {
        pub id: u256,
        pub validated_by: ContractAddress,
        pub completely_validated: bool,
    }

    #[constructor]
    fn constructor(ref self: ContractState, owner: ContractAddress) {
        self.owner.write(owner);
        self.threat_count.write(0);
        self.oracles.write(owner, true);
    }

    #[abi(embed_v0)]
    impl ThreatRegistryImpl of IThreatRegistry<ContractState> {
        fn report_threat(
            ref self: ContractState,
            severity: u8,
            pattern_hash: felt252,
        ) -> u256 {
            let caller = get_caller_address();
            let timestamp = get_block_timestamp();
            
            let id = self.threat_count.read() + 1;
            
            let threat = ThreatPattern {
                id,
                severity,
                pattern_hash,
                reporter: caller,
                validator_count: 0,
                validated: false,
                timestamp,
            };
            
            self.threats.write(id, threat);
            self.threat_count.write(id);
            
            self.emit(ThreatReported {
                id,
                reporter: caller,
                severity,
                pattern_hash,
            });
            
            id
        }

        fn validate_threat(ref self: ContractState, threat_id: u256) {
            let caller = get_caller_address();
            assert!(self.oracles.read(caller), "Only oracles can validate");
            
            let mut threat = self.threats.read(threat_id);
            assert!(threat.id != 0, "Threat does not exist");
            assert!(!threat.validated, "Already validated");
            assert!(!self.threat_validations.read((threat_id, caller)), "Already validated by this oracle");
            
            self.threat_validations.write((threat_id, caller), true);
            threat.validator_count += 1;
            
            // Requires 2 validations to be fully validated
            if threat.validator_count >= 2 {
                threat.validated = true;
            }
            
            let completely_validated = threat.validated;
            self.threats.write(threat_id, threat);
            
            self.emit(ThreatValidated {
                id: threat_id,
                validated_by: caller,
                completely_validated,
            });
        }

        fn get_threat(self: @ContractState, threat_id: u256) -> ThreatPattern {
            self.threats.read(threat_id)
        }

        fn get_threat_count(self: @ContractState) -> u256 {
            self.threat_count.read()
        }

        fn add_oracle(ref self: ContractState, oracle: ContractAddress) {
            let caller = get_caller_address();
            assert!(caller == self.owner.read(), "Only owner can add oracle");
            self.oracles.write(oracle, true);
        }

        fn remove_oracle(ref self: ContractState, oracle: ContractAddress) {
            let caller = get_caller_address();
            assert!(caller == self.owner.read(), "Only owner can remove oracle");
            self.oracles.write(oracle, false);
        }
    }

    #[cfg(test)]
    mod tests {
        use super::{ContractState, ThreatRegistryImpl, constructor, contract_state_for_testing};
        use starknet::ContractAddress;
        use starknet::contract_address_const;
        use starknet::testing::set_caller_address;

        fn OWNER() -> ContractAddress {
            contract_address_const::<0x100>()
        }

        fn ORACLE() -> ContractAddress {
            contract_address_const::<0x200>()
        }

        fn OTHER() -> ContractAddress {
            contract_address_const::<0x400>()
        }

        #[test]
        fn test_threat_registry_initialization() {
            let mut state: ContractState = contract_state_for_testing();
            constructor(ref state, OWNER());
            assert!(ThreatRegistryImpl::get_threat_count(@state) == 0, "Initial threat count should be 0");
        }

        #[test]
        fn test_threat_registry_report_and_validate() {
            let mut state: ContractState = contract_state_for_testing();
            constructor(ref state, OWNER());

            set_caller_address(OWNER());
            let pattern_hash: felt252 = 0xabcdef;
            let threat_id = ThreatRegistryImpl::report_threat(ref state, 3, pattern_hash);

            assert!(threat_id == 1, "First threat ID should be 1");
            assert!(ThreatRegistryImpl::get_threat_count(@state) == 1, "Threat count should be 1");

            let threat = ThreatRegistryImpl::get_threat(@state, threat_id);
            assert!(threat.severity == 3, "Severity mismatch");
            assert!(threat.pattern_hash == pattern_hash, "Pattern hash mismatch");
            assert!(!threat.validated, "Should not be validated initially");

            // First validation by OWNER
            ThreatRegistryImpl::validate_threat(ref state, threat_id);
            let partial = ThreatRegistryImpl::get_threat(@state, threat_id);
            assert!(!partial.validated, "Threat requires 2 validations");
            assert!(partial.validator_count == 1, "Validator count should be 1");

            // Add second oracle and validate
            set_caller_address(OWNER());
            ThreatRegistryImpl::add_oracle(ref state, ORACLE());
            set_caller_address(ORACLE());
            ThreatRegistryImpl::validate_threat(ref state, threat_id);

            let fully_validated = ThreatRegistryImpl::get_threat(@state, threat_id);
            assert!(fully_validated.validated, "Threat should be marked fully validated");
            assert!(fully_validated.validator_count == 2, "Validator count should be 2");
        }

        #[test]
        fn test_threat_registry_oracle_management() {
            let mut state: ContractState = contract_state_for_testing();
            constructor(ref state, OWNER());

            set_caller_address(OWNER());
            ThreatRegistryImpl::add_oracle(ref state, ORACLE());

            // Now ORACLE can report/validate
            set_caller_address(ORACLE());
            let threat_id = ThreatRegistryImpl::report_threat(ref state, 4, 0x112233);
            assert!(threat_id == 1, "Threat ID should be 1");

            // Remove oracle by owner
            set_caller_address(OWNER());
            ThreatRegistryImpl::remove_oracle(ref state, ORACLE());
        }

        #[test]
        #[should_panic(expected: ("Only owner can add oracle",))]
        fn test_threat_registry_unauthorized_add_oracle() {
            let mut state: ContractState = contract_state_for_testing();
            constructor(ref state, OWNER());

            set_caller_address(OTHER());
            ThreatRegistryImpl::add_oracle(ref state, ORACLE());
        }
    }
}
