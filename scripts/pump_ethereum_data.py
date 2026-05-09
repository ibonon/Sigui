import os
import json
import time
import requests
from tqdm import tqdm
from dotenv import load_dotenv

load_dotenv()

REAL_DATA_FILE = r"C:\Users\diass\Sigui\datasets\real_raw\transactions_real.jsonl"
# Etherscan USDC contract address
USDC_CONTRACT = "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48"
API_URL = "https://api.etherscan.io/v2/api"

def fetch_usdc_transfers(start_block, page=1, offset=10000):
    """Fetch USDC transfers from Etherscan API (up to 10k per call)"""
    api_key = os.getenv("ETHERSCAN_API_KEY", "")
    params = {
        "chainid": 1,
        "module": "account",
        "action": "tokentx",
        "contractaddress": USDC_CONTRACT,
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
        return []
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def pump_data(target_count=500000):
    print(f"[*] Starting Ethereum Pump to collect {target_count} real USDC transactions...")
    os.makedirs(os.path.dirname(REAL_DATA_FILE), exist_ok=True)
    
    # Try to find the last block we have
    start_block = 0
    if os.path.exists(REAL_DATA_FILE):
        try:
            with open(REAL_DATA_FILE, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if lines:
                    last_tx = json.loads(lines[-1])
                    start_block = int(last_tx.get("block_number", 0))
        except:
            pass
            
    # If the last block is strangely high (e.g., from another chain like ARC), reset it
    if start_block > 21000000 or start_block == 0:
        start_block = 18000000 # Start from a safe Ethereum mainnet block
        
    print(f"[*] Resuming from Ethereum block {start_block}...")
    
    count = 0
    pbar = tqdm(total=target_count)
    
    with open(REAL_DATA_FILE, 'a', encoding='utf-8') as f:
        while count < target_count:
            # Etherscan returns max 10,000 per request
            txs = fetch_usdc_transfers(start_block, page=1, offset=10000)
            if txs is None or len(txs) == 0:
                print("\n[!] Etherscan rate limit reached. Sleeping 6 seconds to respect free API limits...")
                time.sleep(6)
                continue
                
            for tx in txs:
                # Convert Etherscan format to Sigui format
                formatted_tx = {
                    "chain": "ethereum",
                    "tx_hash": tx["hash"],
                    "from": tx["from"],
                    "to": tx["to"],
                    "amount_usdc": float(tx["value"]) / 1e6, # USDC has 6 decimals
                    "timestamp": int(tx["timeStamp"]),
                    "block_number": int(tx["blockNumber"]),
                    "token": "USDC",
                    "source": "etherscan_tokentx"
                }
                f.write(json.dumps(formatted_tx) + "\n")
                count += 1
                pbar.update(1)
                
                if count >= target_count:
                    break
            
            # Move block window to the last block fetched to continue
            start_block = int(txs[-1]["blockNumber"])
            time.sleep(1) # respect rate limit

    pbar.close()
    print(f"[*] Successfully pumped {count} new real transactions!")

if __name__ == "__main__":
    pump_data(200000) # Download 200,000 extra transactions
