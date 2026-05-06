"""
Generate synthetic blockchain graph images for Imina Na fine-tuning.

Usage:
  python scripts/generate_dogon_dataset.py --total 10000 --out datasets/dogon
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import networkx as nx

    RENDERING_AVAILABLE = True
except Exception:
    plt = None  # type: ignore
    nx = None  # type: ignore
    RENDERING_AVAILABLE = False

PATTERNS = ("DRAIN_STAR", "MIXING_CHAIN", "COORDINATED_CLUSTER", "NORMAL")
LAYOUTS = ("spring", "kamada_kawai", "circular", "shell")


def build_graph(pattern: str, n_nodes: int, rng: random.Random) -> nx.DiGraph:
    g = nx.DiGraph()
    for i in range(n_nodes):
        g.add_node(f"n{i}")

    nodes = list(g.nodes)

    if pattern == "DRAIN_STAR":
        rng.shuffle(nodes)
        hub = nodes[0]
        n_branches = rng.randint(4, n_nodes - 1)
        for i in range(1, n_branches + 1):
            g.add_edge(nodes[i], hub)

    elif pattern == "MIXING_CHAIN":
        rng.shuffle(nodes)
        chain_len = rng.randint(4, n_nodes)
        for i in range(chain_len - 1):
            g.add_edge(nodes[i], nodes[i+1])

    elif pattern == "COORDINATED_CLUSTER":
        rng.shuffle(nodes)
        dst = nodes[0]
        n_cluster = rng.randint(3, max(4, n_nodes // 2))
        for i in range(1, n_cluster):
            g.add_edge(nodes[i], dst)
        start_chain = n_cluster
        available = n_nodes - start_chain
        chain_len = rng.randint(3, available) if available >= 3 else available
        for i in range(start_chain, start_chain + chain_len - 1):
            g.add_edge(nodes[i], nodes[i+1])
        if chain_len > 0 and rng.random() > 0.5:
            g.add_edge(nodes[start_chain + chain_len - 1], dst)

    else:
        edge_count = rng.randint(n_nodes // 2, int(n_nodes * 1.5))
        for _ in range(edge_count):
            a = rng.choice(nodes)
            b = rng.choice(nodes)
            if a != b:
                g.add_edge(a, b)

    if pattern != "NORMAL":
        noise_edges = rng.randint(0, 3)
        for _ in range(noise_edges):
            a = rng.choice(nodes)
            b = rng.choice(nodes)
            if a != b:
                g.add_edge(a, b)

    return g


def compute_layout(g: nx.Graph, name: str, seed: int):
    if name == "spring":
        return nx.spring_layout(g, seed=seed)
    if name == "kamada_kawai":
        return nx.kamada_kawai_layout(g)
    if name == "circular":
        return nx.circular_layout(g)
    return nx.shell_layout(g)


def render_graph(g: nx.DiGraph, layout_name: str, path: Path, seed: int):
    pos = compute_layout(g, layout_name, seed)
    fig = plt.figure(figsize=(4, 4), facecolor="#0d0f2b")
    ax = fig.add_subplot(111)
    ax.set_facecolor("#0d0f2b")
    ax.axis("off")

    node_colors = []
    for n in g.nodes:
        deg = g.in_degree(n) + g.out_degree(n)
        if deg >= 4:
            node_colors.append("#E24B4A")
        elif deg <= 1:
            node_colors.append("#1D9E75")
        else:
            node_colors.append("#f6c90e")

    nx.draw_networkx_nodes(g, pos, node_size=120, node_color=node_colors, linewidths=0.0)
    nx.draw_networkx_edges(g, pos, edge_color="#8b5cf6", arrows=False, width=1.0, alpha=0.9)
    fig.savefig(path, dpi=120, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)


def estimate_edges(pattern: str, n_nodes: int, rng: random.Random) -> int:
    # Approximate edge count to keep metadata simple if networkx isn't used
    noise = rng.randint(0, 3) if pattern != "NORMAL" else 0
    if pattern == "DRAIN_STAR":
        return rng.randint(4, n_nodes - 1) + noise
    if pattern == "MIXING_CHAIN":
        return max(0, rng.randint(4, n_nodes) - 1) + noise
    if pattern == "COORDINATED_CLUSTER":
        n_cluster = rng.randint(3, max(4, n_nodes // 2))
        available = n_nodes - n_cluster
        chain_len = rng.randint(3, available) if available >= 3 else available
        return (n_cluster - 1) + max(0, chain_len - 1) + noise
    return rng.randint(n_nodes // 2, int(n_nodes * 1.5))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--total", type=int, default=10000)
    parser.add_argument("--out", type=str, default="datasets/dogon")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--metadata-only",
        action="store_true",
        help="Generate annotations without image rendering.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    out_dir = Path(args.out)
    metadata_only = args.metadata_only or not RENDERING_AVAILABLE
    images_dir = out_dir / "images"
    if not metadata_only:
        images_dir.mkdir(parents=True, exist_ok=True)
    else:
        out_dir.mkdir(parents=True, exist_ok=True)
        if not RENDERING_AVAILABLE and not args.metadata_only:
            print(
                "[WARN] matplotlib/networkx not installed -> fallback metadata-only mode."
            )
            print(
                "       Install deps for PNG rendering: pip install matplotlib networkx"
            )

    per_pattern = args.total // len(PATTERNS)
    metadata = []
    idx = 0

    for pattern in PATTERNS:
        for _ in range(per_pattern):
            n_nodes = rng.randint(6, 20)
            layout = rng.choice(LAYOUTS)
            g = None
            n_edges = 0
            if nx is not None:
                g = build_graph(pattern, n_nodes, rng)
                n_edges = g.number_of_edges()
            else:
                n_edges = estimate_edges(pattern, n_nodes, rng)
            img_name = f"{idx:05d}_{pattern}.png"
            img_path = images_dir / img_name
            if not metadata_only and g is not None:
                render_graph(g, layout, img_path, seed=rng.randint(0, 10_000))
            metadata.append(
                {
                    "id": idx,
                    "image": str(img_path.as_posix()) if not metadata_only else "",
                    "pattern": pattern,
                    "risk_delta": {
                        "DRAIN_STAR": 0.45,
                        "MIXING_CHAIN": 0.35,
                        "COORDINATED_CLUSTER": 0.40,
                        "NORMAL": 0.0,
                    }[pattern],
                    "n_nodes": n_nodes,
                    "n_edges": n_edges,
                    "layout": layout,
                }
            )
            idx += 1

    (out_dir / "annotations.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    if metadata_only:
        print(f"Generated {len(metadata)} metadata samples in {out_dir} (no PNG files)")
    else:
        print(f"Generated {len(metadata)} samples in {out_dir}")


if __name__ == "__main__":
    main()
