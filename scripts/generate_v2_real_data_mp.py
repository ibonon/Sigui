import os
import json
import random
import networkx as nx
import matplotlib.pyplot as plt
from multiprocessing import Pool, cpu_count
from tqdm import tqdm
import argparse

# Configuration
OUTPUT_DIR = "dataset_v2_real_100k"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
JSONL_FILE = os.path.join(OUTPUT_DIR, "qwen2_vl_real_data.jsonl")
REAL_DATA_FILE = os.path.join("datasets", "real_raw", "transactions_real.jsonl")

import matplotlib
matplotlib.use('Agg') # Force non-interactive backend for speed
import matplotlib.pyplot as plt
plt.style.use('dark_background')

def load_real_transactions():
    txs = []
    if not os.path.exists(REAL_DATA_FILE):
        return []
    with open(REAL_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                txs.append(json.loads(line))
            except:
                pass
    return txs

def get_real_subgraph(txs, window_size=40):
    start_idx = random.randint(0, max(0, len(txs) - window_size - 1))
    chunk = txs[start_idx:start_idx + window_size]
    
    G = nx.DiGraph()
    chain_name = chunk[0].get("chain", "ethereum") if chunk else "ethereum"
    
    for tx in chunk:
        u = tx["from"][:8]
        v = tx["to"][:8]
        amount = float(tx.get("amount_usdc", 0.0))
        G.add_edge(u, v, weight=amount, type="normal", chain=tx.get("chain", "ethereum"))
        G.nodes[u]["role"] = "normal"
        G.nodes[v]["role"] = "normal"
    return G, chain_name

def inject_drain_star(G, num_attackers=15):
    nodes = list(G.nodes())
    if not nodes: return "NORMAL", "Empty graph"
    target = random.choice(nodes)
    G.nodes[target]["role"] = "attacker"
    victims = random.sample(nodes, min(num_attackers, len(nodes)))
    for v in victims:
        if v == target: continue
        G.nodes[v]["role"] = "victim"
        G.add_edge(v, target, weight=random.uniform(500, 5000), type="attack")
        
    cot = (
        f"The topology reveals a highly concentrated DRAIN_STAR pattern embedded within normal "
        f"blockchain traffic. A single central address ({target}) is simultaneously receiving "
        f"large, anomalous USDC transfers from {len(victims)} unrelated peer wallets, strongly indicating "
        f"a synchronized wallet draining or exploit sweep."
    )
    return "DRAIN_STAR", cot

def inject_mixing_chain(G, chain_length=6):
    nodes = list(G.nodes())
    if len(nodes) < chain_length: return "NORMAL", "Graph too small"
    mixers = random.sample(nodes, chain_length)
    mix_amount = random.uniform(1000, 10000)
    for i in range(len(mixers) - 1):
        u, v = mixers[i], mixers[i+1]
        G.nodes[u]["role"] = "mixer"
        G.nodes[v]["role"] = "mixer"
        G.add_edge(u, v, weight=mix_amount * random.uniform(0.98, 1.0), type="attack")
        
    cot = (
        f"A clear MIXING_CHAIN topology is visible cutting through the organic background noise. "
        f"Funds of approximately {mix_amount:.2f} USDC are hopping linearly through {chain_length} "
        f"addresses in rapid succession, a classic laundering heuristic."
    )
    return "MIXING_CHAIN", cot

def process_sample(args):
    i, txs = args
    G, chain_name = get_real_subgraph(txs, window_size=random.randint(30, 80))
    
    choice = random.choice(["DRAIN_STAR", "MIXING_CHAIN", "NORMAL", "NORMAL"])
    if choice == "DRAIN_STAR":
        pattern, cot = inject_drain_star(G, random.randint(8, 25))
        conf, delta = 0.95, 0.45
    elif choice == "MIXING_CHAIN":
        pattern, cot = inject_mixing_chain(G, random.randint(5, 8))
        conf, delta = 0.88, 0.35
    else:
        pattern = "NORMAL"
        conf, delta = 0.80, 0.0
        cot = (
            f"The graph displays purely organic transaction topologies on the {chain_name} network. "
            f"No suspicious clusters, excessive central hubs, or linear laundering chains are detected. "
            f"Background noise shows standard decentralized economic flows."
        )
        
    img_filename = f"real_graph_{i:06d}_{pattern.lower()}.png"
    img_path = os.path.join(IMAGES_DIR, img_filename)
    
    # Render Graph (Optimized for Speed)
    plt.figure(figsize=(7, 7)) # Slightly smaller for faster saving
    pos = nx.spring_layout(G, k=0.3, iterations=12) # Reduced iterations for massive speedup
    
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        role = G.nodes[node].get("role", "normal")
        deg = G.in_degree(node) + G.out_degree(node)
        node_sizes.append(80 + deg * 30)
        if role == "attacker": node_colors.append('#ff3333')
        elif role == "victim": node_colors.append('#33ff33')
        elif role == "mixer": node_colors.append('#ff9933')
        else: node_colors.append('#1f77b4')
            
    edge_colors = ['#ff3333' if G[u][v].get('type') == 'attack' else '#444444' for u, v in G.edges()]
    max_weight = max([G[u][v].get('weight', 1.0) for u, v in G.edges()] + [1.0])
    edge_widths = [min(5.0, (G[u][v].get('weight', 0.0) / max_weight) * 4.0 + 0.5) for u, v in G.edges()]
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9, edgecolors='white')
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, arrowsize=8, alpha=0.5)
    
    plt.axis('off')
    plt.savefig(img_path, dpi=60, bbox_inches='tight', pad_inches=0, facecolor='black') # Lower DPI for faster I/O
    plt.clf() # Clear figure instead of closing all (much faster)
    plt.close()
    
    response_payload = {
        "pattern": pattern, "confidence": conf, "risk_delta": delta,
        "visual_evidence": cot, "model": "Imina-Na-V2-7B-Insane"
    }
    
    entry = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img_path},
                    {"type": "text", "text": f"Analyze this {chain_name} transaction graph topology."}
                ]
            },
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": f"<think>\n{cot}\n</think>\n```json\n{json.dumps(response_payload, indent=2)}\n```"}
                ]
            }
        ]
    }
    return entry

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=100000, help="Number of graphs to generate")
    args = parser.parse_args()
    num_samples = args.samples

    print(f"[*] Loading real transactions from {REAL_DATA_FILE}...")
    txs = load_real_transactions()
    if not txs:
        print("[!] No real transactions found. Please run scripts/pump_ethereum_data.py first.")
        return
        
    print(f"[*] Loaded {len(txs)} real transactions.")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    
    cores = max(1, cpu_count() - 1)
    print(f"[*] Launching Multiprocessing Generator on {cores} cores for {num_samples} samples...")
    
    tasks = [(i, txs) for i in range(num_samples)]
    dataset = []
    
    with Pool(processes=cores) as pool:
        for entry in tqdm(pool.imap_unordered(process_sample, tasks), total=num_samples):
            dataset.append(entry)
            
    with open(JSONL_FILE, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")
            
    print(f"\n[*] INSANE V2 Dataset ({num_samples} samples) generated successfully in '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    main()
