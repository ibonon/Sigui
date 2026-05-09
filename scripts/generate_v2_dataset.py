import os
import json
import random
import uuid
import networkx as nx
import matplotlib.pyplot as plt
from tqdm import tqdm

# Configuration
NUM_SAMPLES = 500
OUTPUT_DIR = "dataset_v2"
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
JSONL_FILE = os.path.join(OUTPUT_DIR, "qwen2_vl_finetune.jsonl")

os.makedirs(IMAGES_DIR, exist_ok=True)

# Graph visual parameters
plt.style.use('dark_background')

def build_drain_star(num_nodes=15, noise=5):
    """Many senders sending to one central attacker."""
    G = nx.DiGraph()
    target = f"attacker_{uuid.uuid4().hex[:4]}"
    G.add_node(target, type="target")
    
    # Attack vectors
    for _ in range(num_nodes):
        sender = f"victim_{uuid.uuid4().hex[:4]}"
        G.add_edge(sender, target, weight=random.uniform(10, 500), type="attack")
        
    # Noise
    for _ in range(noise):
        u = f"noise_{uuid.uuid4().hex[:4]}"
        v = f"noise_{uuid.uuid4().hex[:4]}"
        G.add_edge(u, v, weight=random.uniform(0.1, 5), type="noise")
        
    cot = (
        f"The visual topology shows a massive convergence of {num_nodes} distinct incoming edges "
        f"into a single central node '{target}'. This high-degree incoming star pattern, isolated from "
        f"normal economic loops, is a textbook signature of a wallet draining event."
    )
    return G, "DRAIN_STAR", cot

def build_mixing_chain(chain_length=6, noise=10):
    """Funds moving through a chain of addresses to obfuscate."""
    G = nx.DiGraph()
    nodes = [f"mixer_{uuid.uuid4().hex[:4]}" for _ in range(chain_length)]
    
    for i in range(len(nodes)-1):
        G.add_edge(nodes[i], nodes[i+1], weight=random.uniform(400, 500), type="attack")
        
    for _ in range(noise):
        u = random.choice(nodes) if random.random() > 0.5 else f"noise_{uuid.uuid4().hex[:4]}"
        v = f"noise_{uuid.uuid4().hex[:4]}"
        G.add_edge(u, v, weight=random.uniform(0.1, 5), type="noise")

    cot = (
        f"I observe a long, linear chain of {chain_length} sequential transfers with near-identical "
        f"high-value amounts. The funds move linearly without standard ecosystem interaction, "
        f"indicating an attempt to break tracing heuristics via a mixing chain."
    )
    return G, "MIXING_CHAIN", cot

def build_normal_activity(num_nodes=20):
    """Random scattered activity, cyclic graphs."""
    G = nx.erdos_renyi_graph(num_nodes, 0.15, directed=True)
    G = nx.DiGraph(G)
    for u, v in G.edges():
        G[u][v]['weight'] = random.uniform(0.5, 50)
        G[u][v]['type'] = "normal"
        
    cot = (
        f"The graph displays a decentralized, low-density network with no extreme hubs or "
        f"suspicious sequential chains. Edge weights are uniformly distributed. This resembles "
        f"standard organic agent-to-agent economic activity."
    )
    return G, "NORMAL", cot

def save_graph_image(G, filename):
    plt.figure(figsize=(10, 10))
    pos = nx.spring_layout(G, k=0.5, iterations=50)
    
    # Style logic
    node_colors = []
    node_sizes = []
    for node in G.nodes():
        deg = G.in_degree(node) + G.out_degree(node)
        node_sizes.append(300 + deg * 50)
        node_str = str(node)
        if "attacker" in node_str:
            node_colors.append('#ff3333') # Red
        elif "victim" in node_str:
            node_colors.append('#33ff33') # Green
        elif "mixer" in node_str:
            node_colors.append('#ff9933') # Orange
        else:
            node_colors.append('#66b3ff') # Blue noise/normal
            
    edge_colors = ['#ff3333' if G[u][v]['type'] == 'attack' else '#555555' for u, v in G.edges()]
    edge_widths = [min(5.0, G[u][v]['weight'] / 50.0) + 0.5 for u, v in G.edges()]
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.9, edgecolors='white')
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, arrowsize=15, alpha=0.7)
    
    plt.axis('off')
    plt.tight_layout()
    plt.savefig(filename, dpi=100, bbox_inches='tight', pad_inches=0, facecolor='black')
    plt.close()

def main():
    print(f"[*] Generating Sigui V2 Dataset: True Multimodal Vision graphs ({NUM_SAMPLES} samples)...")
    dataset = []
    
    for i in tqdm(range(NUM_SAMPLES)):
        choice = random.choice(["DRAIN_STAR", "MIXING_CHAIN", "NORMAL", "NORMAL"])
        if choice == "DRAIN_STAR":
            G, pattern, cot = build_drain_star(num_nodes=random.randint(10, 30), noise=random.randint(5, 15))
            conf, delta = 0.95, 0.45
        elif choice == "MIXING_CHAIN":
            G, pattern, cot = build_mixing_chain(chain_length=random.randint(5, 10), noise=random.randint(10, 20))
            conf, delta = 0.88, 0.35
        else:
            G, pattern, cot = build_normal_activity(num_nodes=random.randint(15, 40))
            conf, delta = 0.80, 0.0
            
        img_filename = f"graph_{i:04d}_{pattern.lower()}.png"
        img_path = os.path.join(IMAGES_DIR, img_filename)
        save_graph_image(G, img_path)
        
        # Build Expected JSON payload for the assistant
        response_payload = {
            "pattern": pattern,
            "confidence": conf,
            "risk_delta": delta,
            "visual_evidence": cot,
            "model": "Imina-Na-V2-7B (ROCm Vision)"
        }
        
        # Qwen2-VL ShareGPT multimodal format
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
            
    print(f"[*] V2 Dataset generated successfully in '{OUTPUT_DIR}/'")
    print(f"Images: {NUM_SAMPLES} PNG files")
    print(f"JSONL: {JSONL_FILE} (Ready for LLaMA-Factory / Qwen fine-tuning)")

if __name__ == "__main__":
    main()
