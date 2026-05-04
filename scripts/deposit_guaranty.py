
import sys
import json
import asyncio
from pathlib import Path

# Add project root to path for imports
ROOT = Path(__file__).parent.parent
sys.path.append(str(ROOT))

from web3 import Web3
from config import settings
ABI_PATH = ROOT / "contracts" / "ThreatRegistry.abi.json"

async def deposit(amount_usdc: float):
    if not settings.threat_registry_address or not settings.arc_signer_private_key:
        print("Error: THREAT_REGISTRY_ADDRESS or ARC_SIGNER_PRIVATE_KEY not configured in .env")
        return

    w3 = Web3(Web3.HTTPProvider(settings.arc_rpc_url))
    if not w3.is_connected():
        print("Error: Could not connect to Arc RPC")
        return

    if not ABI_PATH.exists():
        print(f"Error: ABI not found at {ABI_PATH}")
        return

    try:
        # Use utf-8-sig to handle potential BOM from Windows/PowerShell
        abi = json.loads(ABI_PATH.read_text(encoding="utf-8-sig"))
    except Exception:
        # Final fallback
        abi = json.loads(ABI_PATH.read_text(encoding="utf-16"))
    checksum_addr = Web3.to_checksum_address(settings.threat_registry_address)
    contract = w3.eth.contract(address=checksum_addr, abi=abi)
    
    signer_addr = settings.arc_signer_address
    amount_wei = int(amount_usdc * 1_000_000) # Arc native USDC is 6 decimals

    print(f"Depositing {amount_usdc} USDC into Guaranty Fund...")
    print(f"Contract: {checksum_addr}")
    print(f"Signer:   {signer_addr}")

    nonce = w3.eth.get_transaction_count(signer_addr)
    gas_price = w3.eth.gas_price
    
    # Build deposit transaction
    tx = contract.functions.depositGuaranty().build_transaction({
        'chainId': settings.arc_chain_id,
        'from': signer_addr,
        'value': amount_wei,
        'nonce': nonce,
        'gas': 100_000,
        'gasPrice': int(gas_price * 1.15)
    })

    signed = w3.eth.account.sign_transaction(tx, settings.arc_signer_private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    
    print(f"Transaction sent! Hash: {w3.to_hex(tx_hash)}")
    print("Waiting for confirmation...")
    
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
    if receipt.status == 1:
        print("✅ Deposit successful!")
        stats = contract.functions.getStats().call()
        print(f"New Guaranty Fund balance: {stats[2] / 1_000_000:.4f} USDC")
    else:
        print("❌ Deposit failed (transaction reverted)")

if __name__ == "__main__":
    amount = 1.0
    if len(sys.argv) > 1:
        try:
            amount = float(sys.argv[1])
        except ValueError:
            print("Invalid amount, using default 1.0 USDC")
            
    asyncio.run(deposit(amount))
