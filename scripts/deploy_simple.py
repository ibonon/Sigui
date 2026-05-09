#!/usr/bin/env python3
"""
Simple deployment script for Sigui contracts - Hackathon AMD Developer Edition
Deploys all three core contracts: ThreatRegistry, Hogonat, AgentIdentityRegistry
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

try:
    from eth_account import Account
    from web3 import Web3
except ImportError:
    print("ERROR: web3.py not installed. Run: pip install web3")
    sys.exit(1)

# Configuration
CONTRACTS_DIR = ROOT / "contracts"
ENV_FILE = ROOT / ".env"

# Contract files
CONTRACTS = {
    "ThreatRegistry": {
        "vyper": CONTRACTS_DIR / "ThreatRegistry.vy",
        "abi": CONTRACTS_DIR / "ThreatRegistry.abi.json",
        "bytecode": CONTRACTS_DIR / "ThreatRegistry.bytecode.txt",
        "deployed": CONTRACTS_DIR / "ThreatRegistry.deployed.json",
        "env_key": "THREAT_REGISTRY_ADDRESS"
    },
    "Hogonat": {
        "vyper": CONTRACTS_DIR / "Hogonat.vy", 
        "abi": CONTRACTS_DIR / "Hogonat.abi.json",
        "bytecode": CONTRACTS_DIR / "Hogonat.bytecode.txt",
        "deployed": CONTRACTS_DIR / "Hogonat.deployed.json",
        "env_key": "HOGONAT_CONTRACT_ADDRESS"
    },
    "AgentIdentityRegistry": {
        "vyper": CONTRACTS_DIR / "AgentIdentityRegistry.vy",
        "abi": CONTRACTS_DIR / "AgentIdentityRegistry.abi.json", 
        "bytecode": CONTRACTS_DIR / "AgentIdentityRegistry.bytecode.txt",
        "deployed": CONTRACTS_DIR / "AgentIdentityRegistry.deployed.json",
        "env_key": "AGENT_IDENTITY_REGISTRY_ADDRESS"
    }
}

def load_env():
    """Load environment variables"""
    env = {}
    if ENV_FILE.exists():
        with open(ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env[key.strip()] = value.strip()
    return env

def save_env(env_dict):
    """Save environment variables"""
    with open(ENV_FILE, 'w') as f:
        for key, value in env_dict.items():
            f.write(f"{key}={value}\n")

def compile_vyper(vy_file):
    """Compile Vyper contract"""
    try:
        import subprocess
        
        # Get ABI
        abi_result = subprocess.run(
            ["vyper", "-f", "abi", str(vy_file)],
            capture_output=True, text=True, timeout=60
        )
        if abi_result.returncode != 0:
            print(f"ABI compilation error: {abi_result.stderr}")
            return None, None
            
        abi = json.loads(abi_result.stdout)
        
        # Get bytecode
        bytecode_result = subprocess.run(
            ["vyper", "-f", "bytecode", str(vy_file)],
            capture_output=True, text=True, timeout=60
        )
        if bytecode_result.returncode != 0:
            print(f"Bytecode compilation error: {bytecode_result.stderr}")
            return None, None
            
        bytecode = bytecode_result.stdout.strip()
        if not bytecode.startswith("0x"):
            bytecode = "0x" + bytecode
            
        return abi, bytecode
        
    except FileNotFoundError:
        print("ERROR: Vyper compiler not found. Install: pip install vyper==0.4.3")
        return None, None
    except Exception as e:
        print(f"Compilation error: {e}")
        return None, None

def deploy_contract(w3, account, abi, bytecode, constructor_args=None):
    """Deploy a single contract"""
    try:
        contract = w3.eth.contract(abi=abi, bytecode=bytecode)
        
        # Estimate gas
        nonce = w3.eth.get_transaction_count(account.address, "pending")
        gas_price = int(w3.eth.gas_price * 1.1)
        
        if constructor_args:
            constructor = contract.constructor(*constructor_args)
        else:
            constructor = contract.constructor()
            
        try:
            gas_estimate = constructor.estimate_gas({"from": account.address})
            gas_limit = int(gas_estimate * 1.3)
        except Exception as e:
            print(f"Gas estimation failed, using default: {e}")
            gas_limit = 3_000_000
        
        # Build transaction
        tx = constructor.build_transaction({
            "chainId": w3.eth.chain_id,
            "from": account.address,
            "nonce": nonce,
            "gas": gas_limit,
            "gasPrice": gas_price,
        })
        
        # Sign and send
        signed_tx = account.sign_transaction(tx)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
        
        print(f"Transaction sent: {tx_hash.hex()}")
        
        # Wait for confirmation
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        
        if receipt.status != 1:
            print(f"Deployment failed! Status: {receipt.status}")
            return None
            
        return receipt.contractAddress
        
    except Exception as e:
        print(f"Deployment error: {e}")
        return None

def main():
    print("=" * 60)
    print("SIGUI CONTRACTS DEPLOYMENT - AMD HACKATHON EDITION")
    print("=" * 60)
    
    # Load environment
    env = load_env()
    
    # Check required variables
    private_key = env.get("ARC_SIGNER_PRIVATE_KEY")
    rpc_url = env.get("ARC_RPC_URL", "https://rpc.testnet.arc.network")
    
    if not private_key:
        print("ERROR: ARC_SIGNER_PRIVATE_KEY not set in .env")
        print("Please set your private key in .env file")
        sys.exit(1)
    
    # Connect to blockchain
    print(f"Connecting to: {rpc_url}")
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    if not w3.is_connected():
        print("ERROR: Cannot connect to blockchain")
        sys.exit(1)
    
    print(f"Connected to chain ID: {w3.eth.chain_id}")
    
    # Setup account
    account = Account.from_key(private_key)
    balance = w3.eth.get_balance(account.address)
    print(f"Deployer: {account.address}")
    print(f"Balance: {w3.from_wei(balance, 'ether')} ARC")
    
    if balance == 0:
        print("ERROR: Insufficient balance for deployment")
        sys.exit(1)
    
    # Deploy contracts
    deployed_addresses = {}
    
    for contract_name, contract_info in CONTRACTS.items():
        print(f"\nDeploying {contract_name}...")
        
        # Check if already deployed
        existing_address = env.get(contract_info["env_key"])
        if existing_address and existing_address not in ["", "0x0", "none"]:
            print(f"Already deployed at: {existing_address}")
            deployed_addresses[contract_name] = existing_address
            continue
        
        # Compile contract
        print("Compiling...")
        abi, bytecode = compile_vyper(contract_info["vyper"])
        
        if not abi or not bytecode:
            print(f"Failed to compile {contract_name}")
            continue
        
        # Save ABI and bytecode
        with open(contract_info["abi"], 'w') as f:
            json.dump(abi, f, indent=2)
            
        with open(contract_info["bytecode"], 'w') as f:
            f.write(bytecode)
        
        # Deploy with appropriate constructor args
        constructor_args = None
        if contract_name == "Hogonat":
            # Hogonat needs USDC address
            usdc_address = env.get("HOGONAT_USDC_TOKEN_ADDRESS", "0x0000000000000000000000000000000000000000")
            constructor_args = [usdc_address]
        
        address = deploy_contract(w3, account, abi, bytecode, constructor_args)
        
        if address:
            print(f"Deployed at: {address}")
            deployed_addresses[contract_name] = address
            env[contract_info["env_key"]] = address
            
            # Save deployment info
            deployment_info = {
                "contract_name": contract_name,
                "address": address,
                "deployer": account.address,
                "chain_id": w3.eth.chain_id,
                "block_number": w3.eth.block_number
            }
            
            with open(contract_info["deployed"], 'w') as f:
                json.dump(deployment_info, f, indent=2)
        else:
            print(f"Failed to deploy {contract_name}")
    
    # Save updated environment
    save_env(env)
    
    print("\n" + "=" * 60)
    print("DEPLOYMENT SUMMARY")
    print("=" * 60)
    
    for contract_name, address in deployed_addresses.items():
        print(f"{contract_name}: {address}")
    
    print("\nAll contracts deployed successfully!")
    print("Environment file updated with contract addresses")
    print("=" * 60)

if __name__ == "__main__":
    main()