import os
import json
import time
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

REAL_DATA_FILE = r"C:\Users\diass\Sigui\datasets\real_raw\transactions_real.jsonl"
API_URL = "https://api.etherscan.io/v2/api"

CHAINS = {
    "ethereum": {"chainid": 1, "usdc": "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "start_block": 19000000},
    "arbitrum": {"chainid": 42161, "usdc": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "start_block": 150000000},
    "polygon": {"chainid": 137, "usdc": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "start_block": 50000000}
}

def count_chains():
    """Counts the number of transactions per chain in the dataset."""
    counts = {"ethereum": 0, "arbitrum": 0, "polygon": 0, "base": 0}
    if not os.path.exists(REAL_DATA_FILE): return counts
    
    print("[*] Analyzing current dataset balance...")
    with open(REAL_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                tx = json.loads(line)
                chain = tx.get("chain", "ethereum") # default to ethereum if missing
                if chain in counts:
                    counts[chain] += 1
            except:
                pass
    return counts

def fetch_usdc_transfers(chain_id, contract, start_block, page=1, offset=10000):
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    params = {
        "chainid": chain_id, "module": "account", "action": "tokentx",
        "contractaddress": contract, "page": page, "offset": offset,
        "startblock": start_block, "sort": "asc", "apikey": api_key
    }
    try:
        response = requests.get(API_URL, params=params)
        data = response.json()
        if data["status"] == "1" and data["message"] == "OK":
            return data["result"]
    except:
        pass
    return None

def pump_missing_data():
    counts = count_chains()
    max_count = max(counts.values())
    print(f"\n[*] Current Distribution: {counts}")
    print(f"[*] Target for perfectly balanced dataset: {max_count} per chain")
    
    with open(REAL_DATA_FILE, 'a', encoding='utf-8') as f:
        for chain_name, chain_info in CHAINS.items():
            missing = max_count - counts[chain_name]
            if missing <= 0:
                print(f"[*] {chain_name.upper()} is already balanced ({counts[chain_name]}). Skipping.")
                continue
                
            print(f"\n[*] Pumping {missing} missing transactions for {chain_name.upper()}...")
            start_block = chain_info["start_block"]
            count = 0
            pbar = tqdm(total=missing)
            
            while count < missing:
                txs = fetch_usdc_transfers(chain_info["chainid"], chain_info["usdc"], start_block)
                if not txs:
                    time.sleep(6)
                    continue
                    
                for tx in txs:
                    formatted_tx = {
                        "chain": chain_name, "tx_hash": tx["hash"], "from": tx["from"], "to": tx["to"],
                        "amount_usdc": float(tx["value"]) / 1e6, "timestamp": int(tx["timeStamp"]),
                        "block_number": int(tx["blockNumber"]), "token": "USDC",
                        "source": f"etherscan_v2_balance"
                    }
                    f.write(json.dumps(formatted_tx) + "\n")
                    count += 1
                    pbar.update(1)
                    if count >= missing: break
                
                start_block = int(txs[-1]["blockNumber"])
                time.sleep(1)
            pbar.close()

if __name__ == "__main__":
    pump_missing_data()
    print("\n[*] Dataset is now PERFECTLY BALANCED! ⚖️")
