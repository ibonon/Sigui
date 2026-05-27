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
    use starknet::storage::{Map, StoragePointerReadAccess, StoragePointerWriteAccess, StorageMapReadAccess, StorageMapWriteAccess};

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
}
