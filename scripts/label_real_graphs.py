"""
Build graph windows from real transactions and generate weak labels for Sigui.

Input:
  datasets/real_raw/transactions_real.jsonl

Output:
  datasets/real_labeled/annotations_real.json
  datasets/real_labeled/train.json
  datasets/real_labeled/val.json
  datasets/real_labeled/test.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import networkx as nx

PATTERNS = ("DRAIN_STAR", "MIXING_CHAIN", "COORDINATED_CLUSTER", "NORMAL")


@dataclass
class TxRow:
    chain: str
    tx_hash: str
    from_addr: str
    to_addr: str
    amount_usdc: float
    timestamp: int


def load_jsonl(path: Path) -> list[TxRow]:
    rows: list[TxRow] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            rows.append(
                TxRow(
                    chain=str(obj.get("chain", "unknown")),
                    tx_hash=str(obj.get("tx_hash", "")),
                    from_addr=str(obj.get("from", "")).lower(),
                    to_addr=str(obj.get("to", "")).lower(),
                    amount_usdc=float(obj.get("amount_usdc", 0.0) or 0.0),
                    timestamp=int(obj.get("timestamp", 0) or 0),
                )
            )
    return rows


def chunk_by_window(rows: list[TxRow], window_s: int) -> list[list[TxRow]]:
    if not rows:
        return []
    rows = sorted(rows, key=lambda x: x.timestamp)
    chunks: list[list[TxRow]] = []
    start = rows[0].timestamp
    cur: list[TxRow] = []
    for r in rows:
        if r.timestamp - start > window_s and cur:
            chunks.append(cur)
            cur = []
            start = r.timestamp
        cur.append(r)
    if cur:
        chunks.append(cur)
    return chunks


def pattern_rules(g: nx.DiGraph, txs: list[TxRow]) -> tuple[str, float, str]:
    if g.number_of_nodes() == 0:
        return "NORMAL", 0.5, "empty_graph"

    in_degrees = dict(g.in_degree())
    out_degrees = dict(g.out_degree())
    max_in = max(in_degrees.values()) if in_degrees else 0
    max_out = max(out_degrees.values()) if out_degrees else 0
    n_edges = g.number_of_edges()
    n_nodes = g.number_of_nodes()

    # DRAIN_STAR: one destination with many unique sources
    if max_in >= 8:
        return "DRAIN_STAR", 0.9, f"max_in_degree={max_in}"

    # MIXING_CHAIN: long directed path
    try:
        longest = 0
        for src in g.nodes:
            for dst in g.nodes:
                if src == dst:
                    continue
                if nx.has_path(g, src, dst):
                    p = nx.shortest_path_length(g, src, dst)
                    longest = max(longest, p)
        if longest >= 5:
            return "MIXING_CHAIN", 0.86, f"longest_path={longest}"
    except Exception:
        pass

    # COORDINATED_CLUSTER: many senders + medium hubs
    if n_nodes >= 8 and n_edges >= 10 and max_in >= 4 and max_out >= 2:
        return "COORDINATED_CLUSTER", 0.82, (
            f"nodes={n_nodes},edges={n_edges},max_in={max_in},max_out={max_out}"
        )

    return "NORMAL", 0.72, f"nodes={n_nodes},edges={n_edges},max_in={max_in}"


def graph_features(g: nx.DiGraph, txs: list[TxRow]) -> dict[str, Any]:
    n_nodes = g.number_of_nodes()
    n_edges = g.number_of_edges()
    total_amount = sum(t.amount_usdc for t in txs)
    avg_amount = total_amount / max(1, len(txs))
    in_degrees = [d for _, d in g.in_degree()]
    out_degrees = [d for _, d in g.out_degree()]
    density = nx.density(g) if n_nodes > 1 else 0.0
    return {
        "n_nodes": n_nodes,
        "n_edges": n_edges,
        "n_txs": len(txs),
        "total_amount_usdc": round(total_amount, 6),
        "avg_amount_usdc": round(avg_amount, 6),
        "max_in_degree": max(in_degrees) if in_degrees else 0,
        "max_out_degree": max(out_degrees) if out_degrees else 0,
        "density": round(float(density), 6),
    }


def risk_delta_for(pattern: str) -> float:
    return {
        "DRAIN_STAR": 0.45,
        "MIXING_CHAIN": 0.35,
        "COORDINATED_CLUSTER": 0.40,
        "NORMAL": 0.0,
    }.get(pattern, 0.0)


def assign_split(graph_id: str) -> str:
    h = int(hashlib.sha256(graph_id.encode()).hexdigest()[:8], 16) % 100
    if h < 80:
        return "train"
    if h < 90:
        return "val"
    return "test"


def build_annotations(rows: list[TxRow], window_s: int, min_edges: int) -> list[dict[str, Any]]:
    by_chain: dict[str, list[TxRow]] = defaultdict(list)
    for r in rows:
        if r.from_addr and r.to_addr and r.timestamp > 0:
            by_chain[r.chain].append(r)

    out: list[dict[str, Any]] = []
    for chain, chain_rows in by_chain.items():
        for chunk in chunk_by_window(chain_rows, window_s=window_s):
            g = nx.DiGraph()
            for tx in chunk:
                if tx.from_addr == tx.to_addr:
                    continue
                g.add_edge(tx.from_addr, tx.to_addr, amount_usdc=tx.amount_usdc, tx_hash=tx.tx_hash)

            if g.number_of_edges() < min_edges:
                continue

            pattern, confidence, evidence = pattern_rules(g, chunk)
            feats = graph_features(g, chunk)
            graph_id = hashlib.sha256(
                f"{chain}:{chunk[0].timestamp}:{chunk[-1].timestamp}:{g.number_of_edges()}:{g.number_of_nodes()}".encode()
            ).hexdigest()[:16]
            out.append(
                {
                    "graph_id": graph_id,
                    "chain": chain,
                    "label_source": "weak_rules_on_real_chain_data",
                    "pattern": pattern,
                    "label_confidence": round(confidence, 4),
                    "risk_delta": risk_delta_for(pattern),
                    "visual_evidence": evidence,
                    "window": {
                        "start_ts": chunk[0].timestamp,
                        "end_ts": chunk[-1].timestamp,
                        "duration_s": max(0, chunk[-1].timestamp - chunk[0].timestamp),
                    },
                    "features": feats,
                    "split": assign_split(graph_id),
                }
            )
    return out


def write_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="datasets/real_raw/transactions_real.jsonl")
    parser.add_argument("--out", type=str, default="datasets/real_labeled")
    parser.add_argument("--window-seconds", type=int, default=900)
    parser.add_argument("--min-edges", type=int, default=6)
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        raise FileNotFoundError(f"Missing input file: {in_path}")
    rows = load_jsonl(in_path)
    annotations = build_annotations(
        rows=rows,
        window_s=max(60, args.window_seconds),
        min_edges=max(2, args.min_edges),
    )
    out_dir = Path(args.out)
    write_json(out_dir / "annotations_real.json", annotations)
    write_json(out_dir / "train.json", [a for a in annotations if a["split"] == "train"])
    write_json(out_dir / "val.json", [a for a in annotations if a["split"] == "val"])
    write_json(out_dir / "test.json", [a for a in annotations if a["split"] == "test"])

    counts: dict[str, int] = {k: 0 for k in PATTERNS}
    for a in annotations:
        counts[a["pattern"]] = counts.get(a["pattern"], 0) + 1
    print(json.dumps({"total_graphs": len(annotations), "pattern_counts": counts}, indent=2))
    print(f"Wrote labeled dataset to {out_dir}")


if __name__ == "__main__":
    main()
