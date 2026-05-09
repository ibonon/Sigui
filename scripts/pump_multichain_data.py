import os
import json
import time
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

REAL_DATA_FILE = r"C:\Users\diass\Sigui\datasets\real_raw\transactions_real.jsonl"
API_URL = "https://api.etherscan.io/v2/api"

# Configuration Multichain pour Etherscan V2
CHAINS = {
    "ethereum": {
        "chainid": 1,
        "usdc": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        "start_block": 19000000 # Récents blocs Ethereum
    },
    "arbitrum": {
        "chainid": 42161,
        "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
        "start_block": 150000000 # Récents blocs Arbitrum
    },
    "polygon": {
        "chainid": 137,
        "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
        "start_block": 50000000 # Récents blocs Polygon
    }
}

def fetch_usdc_transfers(chain_id, contract, start_block, page=1, offset=10000):
    """Fetch USDC transfers from Etherscan API V2"""
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    params = {
        "chainid": chain_id,
        "module": "account",
        "action": "tokentx",
        "contractaddress": contract,
        "page": page,
        "offset": offset,
        "startblock": start_block,
        "sort": "asc",
        "apikey": api_key
    }
    try:
        response = requests.get(API_URL, params=params)
        data = response.json()
        if data["status"] == "1" and data["message"] == "OK":
            return data["result"]
        return None
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def pump_data(target_per_chain=200000):
    total_target = target_per_chain * len(CHAINS)
    print(f"[*] Starting Multichain Pump to collect {total_target} real USDC transactions...")
    os.makedirs(os.path.dirname(REAL_DATA_FILE), exist_ok=True)
    
    print(f"[*] Goal: {target_per_chain} transactions per chain ({', '.join(CHAINS.keys())})")
    
    total_count = 0
    pbar = tqdm(total=total_target)
    
    with open(REAL_DATA_FILE, 'a', encoding='utf-8') as f:
        for chain_name, chain_info in CHAINS.items():
            print(f"\n[*] Switching to {chain_name.upper()}...")
            count = 0
            start_block = chain_info["start_block"]
            
            while count < target_per_chain:
                txs = fetch_usdc_transfers(chain_info["chainid"], chain_info["usdc"], start_block)
                
                if txs is None or len(txs) == 0:
                    print(f"\n[!] Rate limit or end of {chain_name} data. Sleeping 6 seconds...")
                    time.sleep(6)
                    continue
                    
                for tx in txs:
                    # Convert format
                    formatted_tx = {
                        "chain": chain_name,
                        "tx_hash": tx["hash"],
                        "from": tx["from"],
                        "to": tx["to"],
                        "amount_usdc": float(tx["value"]) / 1e6, # USDC has 6 decimals
                        "timestamp": int(tx["timeStamp"]),
                        "block_number": int(tx["blockNumber"]),
                        "token": "USDC",
                        "source": f"etherscan_v2_{chain_name}"
                    }
                    f.write(json.dumps(formatted_tx) + "\n")
                    count += 1
                    total_count += 1
                    pbar.update(1)
                    
                    if count >= target_per_chain or total_count >= total_target:
                        break
                
                start_block = int(txs[-1]["blockNumber"])
                time.sleep(1) # respect rate limit between pages
                
            if total_count >= total_target:
                break

    pbar.close()
    print(f"\n[*] Successfully pumped {total_count} MULTICHAIN transactions!")

if __name__ == "__main__":
    pump_data(200000) # Collect 200,000 from EACH chain (800k total)
