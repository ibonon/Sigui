import os
import json
import random
import networkx as nx
import matplotlib.pyplot as plt
from tqdm import tqdm

# Configuration
NUM_SAMPLES = 500
OUTPUT_DIR = "dataset_v2_real"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
JSONL_FILE = os.path.join(OUTPUT_DIR, "qwen2_vl_real_data.jsonl")
REAL_DATA_FILE = r"C:\Users\diass\Sigui\datasets\real_raw\transactions_real.jsonl"

os.makedirs(IMAGES_DIR, exist_ok=True)
plt.style.use('dark_background')

def load_real_transactions():
    """Load the historical Etherscan/Arc data."""
    txs = []
    with open(REAL_DATA_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            try:
                txs.append(json.loads(line))
            except:
                pass
    return txs

def get_real_subgraph(txs, window_size=40):
    """Get a continuous chunk of real transactions to form background noise."""
    start_idx = random.randint(0, max(0, len(txs) - window_size - 1))
    chunk = txs[start_idx:start_idx + window_size]
    
    G = nx.DiGraph()
    for tx in chunk:
        u = tx["from"]
        v = tx["to"]
        amount = float(tx.get("amount_usdc", 0.0))
        # Keep node IDs short for visualization speed/memory
        u_short = u[:8]
        v_short = v[:8]
        G.add_edge(u_short, v_short, weight=amount, type="normal")
        G.nodes[u_short]["role"] = "normal"
        G.nodes[v_short]["role"] = "normal"
    return G

def inject_drain_star(G, num_attackers=15):
    nodes = list(G.nodes())
    if not nodes: return "NORMAL", "Empty graph"
    
    # Pick a random real node to be the target (the drainer)
    target = random.choice(nodes)
    G.nodes[target]["role"] = "attacker"
    
    # Pick random real nodes to act as compromised victims
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
    
    # Pick real nodes to form a chain
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

def save_graph_image(G, filename):
    plt.figure(figsize=(12, 12))
    pos = nx.spring_layout(G, k=0.3, iterations=50)
    
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        role = G.nodes[node].get("role", "normal")
        deg = G.in_degree(node) + G.out_degree(node)
        node_sizes.append(100 + deg * 40)
        
        if role == "attacker": node_colors.append('#ff3333') # Red
        elif role == "victim": node_colors.append('#33ff33') # Green
        elif role == "mixer": node_colors.append('#ff9933') # Orange
        else: node_colors.append('#1f77b4') # Blue background
            
    edge_colors = ['#ff3333' if G[u][v].get('type') == 'attack' else '#444444' for u, v in G.edges()]
    
    # Normalize edge widths securely to prevent math errors
    max_weight = max([G[u][v].get('weight', 1.0) for u, v in G.edges()] + [1.0])
    edge_widths = [min(6.0, (G[u][v].get('weight', 0.0) / max_weight) * 5.0 + 0.5) for u, v in G.edges()]
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9, edgecolors='white')
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, arrowsize=10, alpha=0.5)
    
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(filename, dpi=100, bbox_inches='tight', pad_inches=0, facecolor='black')
    plt.close()

def main():
    print(f"[*] Loading real transactions from {REAL_DATA_FILE}...")
    txs = load_real_transactions()
    print(f"[*] Loaded {len(txs)} real transactions.")
    
    dataset = []
    
    print(f"[*] Generating Hybrid V2 Dataset ({NUM_SAMPLES} samples)...")
    for i in tqdm(range(NUM_SAMPLES)):
        # Base organic background noise
        G = get_real_subgraph(txs, window_size=random.randint(30, 80))
        
        choice = random.choice(["DRAIN_STAR", "MIXING_CHAIN", "NORMAL", "NORMAL"])
        if choice == "DRAIN_STAR":
            pattern, cot = inject_drain_star(G, num_attackers=random.randint(8, 25))
            conf, delta = 0.95, 0.45
        elif choice == "MIXING_CHAIN":
            pattern, cot = inject_mixing_chain(G, chain_length=random.randint(5, 8))
            conf, delta = 0.88, 0.35
        else:
            pattern = "NORMAL"
            conf, delta = 0.80, 0.0
            cot = (
                "The graph displays purely organic transaction topologies. No suspicious clusters, "
                "excessive central hubs, or linear laundering chains are detected. Background noise "
                "shows standard decentralized economic flows."
            )
            
        img_filename = f"real_graph_{i:04d}_{pattern.lower()}.png"
        img_path = os.path.join(IMAGES_DIR, img_filename)
        save_graph_image(G, img_path)
        
        response_payload = {
            "pattern": pattern,
            "confidence": conf,
            "risk_delta": delta,
            "visual_evidence": cot,
            "model": "Imina-Na-V2-7B (Real-Data Hybrid)"
        }
        
        entry = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": img_path},
                        {"type": "text", "text": "Analyze this transaction graph topology. Reason through the visual structures (colors, hubs, chains) then output a JSON response with the risk signal."}
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
        dataset.append(entry)
        
    with open(JSONL_FILE, 'w', encoding='utf-8') as f:
        for entry in dataset:
            f.write(json.dumps(entry) + "\n")
            
    print(f"[*] Real-Data V2 Dataset generated successfully in '{OUTPUT_DIR}/'")

if __name__ == "__main__":
    main()
