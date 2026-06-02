#[test_only]
module sigui::reputation_tests {
    use std::signer;
    use aptos_framework::account;
    use aptos_framework::timestamp;
    use sigui::agent_reputation;

    #[test(admin = @sigui)]
    public fun test_initialization(admin: &signer) {
        agent_reputation::initialize(admin);
        assert!(agent_reputation::total_agents(signer::address_of(admin)) == 0, 1);
    }

    #[test(admin = @sigui, agent1 = @0x123)]
    public fun test_register_agent(admin: &signer, agent1: &signer) {
        timestamp::set_time_has_started_for_testing(&account::create_account_for_test(@0x1));
        
        agent_reputation::initialize(admin);
        
        let admin_addr = signer::address_of(admin);
        let agent1_addr = signer::address_of(agent1);
        let did = b"did:sigui:aptos:agent1";
        
        agent_reputation::register_agent(agent1, admin_addr, did);
        
        assert!(agent_reputation::total_agents(admin_addr) == 1, 1);
        assert!(agent_reputation::get_reputation(admin_addr, agent1_addr) == 500, 2); // Initial reputation is 500
    }

    #[test(admin = @sigui, agent1 = @0x123)]
    public fun test_update_reputation(admin: &signer, agent1: &signer) {
        timestamp::set_time_has_started_for_testing(&account::create_account_for_test(@0x1));
        
        agent_reputation::initialize(admin);
        
        let admin_addr = signer::address_of(admin);
        let agent1_addr = signer::address_of(agent1);
        
        agent_reputation::register_agent(agent1, admin_addr, b"did:sigui:aptos:agent1");
        
        // Admin acts as oracle initially
        agent_reputation::update_reputation(admin, admin_addr, agent1_addr, 50, true, b"Good behavior");
        
        // 500 + 50 = 550
        assert!(agent_reputation::get_reputation(admin_addr, agent1_addr) == 550, 3);
        
        // Penalty
        agent_reputation::update_reputation(admin, admin_addr, agent1_addr, 100, false, b"Failed validation");
        
        // 550 - 100 = 450
        assert!(agent_reputation::get_reputation(admin_addr, agent1_addr) == 450, 4);
    }

    #[test(admin = @sigui, agent1 = @0x123)]
    #[expected_failure(abort_code = agent_reputation::ENOT_AUTHORIZED)]
    public fun test_unauthorized_reputation_update(admin: &signer, agent1: &signer) {
        timestamp::set_time_has_started_for_testing(&account::create_account_for_test(@0x1));
        
        agent_reputation::initialize(admin);
        let admin_addr = signer::address_of(admin);
        let agent1_addr = signer::address_of(agent1);
        
        agent_reputation::register_agent(agent1, admin_addr, b"did:sigui:aptos:agent1");
        
        // Agent1 cannot update its own reputation
        agent_reputation::update_reputation(agent1, admin_addr, agent1_addr, 500, true, b"Hack");
    }

    #[test(admin = @sigui, agent1 = @0x123)]
    public fun test_slash_agent(admin: &signer, agent1: &signer) {
        timestamp::set_time_has_started_for_testing(&account::create_account_for_test(@0x1));
        
        agent_reputation::initialize(admin);
        let admin_addr = signer::address_of(admin);
        let agent1_addr = signer::address_of(agent1);
        
        agent_reputation::register_agent(agent1, admin_addr, b"did:sigui:aptos:agent1");
        
        agent_reputation::slash_agent(admin, admin_addr, agent1_addr, b"Malicious threat detected");
        
        // Reputation should be 0 after slashing
        assert!(agent_reputation::get_reputation(admin_addr, agent1_addr) == 0, 5);
    }
}
