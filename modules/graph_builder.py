"""
Sigui P4 — Build graph payloads for Imina Na from recent local activity.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from modules.memory import memory
from ecosystem.address_pool import AddressPool


class GraphBuilderService:
    """Assemble a compact graph payload from recent flows and decisions."""

    def _add_node(
        self,
        nodes: list[dict[str, Any]],
        seen: set[str],
        node_id: str,
        node_type: str,
        **attrs: Any,
    ) -> None:
        if node_id in seen:
            return
        node = {"id": node_id, "type": node_type}
        node.update(attrs)
        nodes.append(node)
        seen.add(node_id)

    def _focus_destination_stats(
        self,
        destination: str,
        recent_flows: list[Any],
        peer_decisions: list[Any],
    ) -> dict[str, Any]:
        dest_key = (destination or "").lower()
        flow_hits = [
            row for row in recent_flows if str(row["destination"] or "").lower() == dest_key
        ]
        peer_hits = [
            row
            for row in peer_decisions
            if str(row["destination"] or "").lower() == dest_key
        ]
        peer_senders = {
            str(row["agent_id"] or "")
            for row in peer_hits
            if str(row["agent_id"] or "")
        }
        flow_chains = {
            str(row["chain"] or "arc").lower()
            for row in flow_hits
            if str(row["chain"] or "")
        }
        return {
            "tx_count": len(flow_hits),
            "total_amount": round(
                sum(float(row["amount_usdc"] or 0.0) for row in flow_hits), 6
            ),
            "chain_count": len(flow_chains),
            "unique_peer_senders": len(peer_senders),
        }

    def _infer_pattern(
        self,
        summary: dict[str, Any],
        current_chain: str,
    ) -> tuple[str, float, float, str]:
        focus_tx_count = int(summary.get("focus_tx_count", 0) or 0)
        focus_peer_senders = int(summary.get("focus_unique_peer_senders", 0) or 0)
        chain_count = int(summary.get("chain_count", 0) or 0)
        unique_destinations = int(summary.get("unique_destinations", 0) or 0)
        tx_count = int(summary.get("tx_count", 0) or 0)
        total_amount = float(summary.get("total_amount", 0.0) or 0.0)
        dominant_chain = str(summary.get("dominant_chain") or current_chain or "arc")
        dest = str(summary.get("focus_destination", "")).lower()
        is_safe = dest in [addr.lower() for addr in AddressPool.KNOWN_SAFE]

        if (focus_peer_senders >= 10 or focus_tx_count >= 30) and not is_safe:
            return (
                "DRAIN_STAR",
                0.88,
                0.45,
                (
                    f"Destination receives concentrated activity "
                    f"(focus_tx={focus_tx_count}, peer_senders={focus_peer_senders})."
                ),
            )

        if chain_count >= 2 and unique_destinations >= 5 and tx_count >= 15:
            return (
                "MIXING_CHAIN",
                0.83,
                0.35,
                (
                    f"Activity spans {chain_count} chains and {unique_destinations} "
                    f"destinations with rotation toward {dominant_chain}."
                ),
            )

        if focus_peer_senders >= 5 and unique_destinations >= 5 and total_amount >= 5.0:
            return (
                "COORDINATED_CLUSTER",
                0.8,
                0.40,
                (
                    f"Multiple senders and destinations cluster around the focal path "
                    f"(peer_senders={focus_peer_senders}, destinations={unique_destinations})."
                ),
            )

        return (
            "NORMAL",
            0.72,
            0.0,
            (
                f"No dominant hostile topology detected "
                f"(tx={tx_count}, destinations={unique_destinations}, chains={chain_count})."
            ),
        )

    async def build_for_action(
        self,
        agent_id: str,
        destination: str,
        chain: str,
        amount_usdc: float,
        window_minutes: int = 10,
        flow_limit: int = 24,
        peer_limit: int = 24,
    ) -> dict[str, Any]:
        recent_flows = await memory.run_query(
            """
            SELECT destination, chain, amount_usdc, timestamp
            FROM flow_windows
            WHERE agent_id = ?
              AND timestamp > datetime('now', ? || ' minutes')
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (agent_id, f"-{window_minutes}", flow_limit),
            fetch="all",
        ) or []

        peer_decisions = await memory.run_query(
            """
            SELECT agent_id, destination, chain, amount_usdc, decision, timestamp
            FROM decisions
            WHERE destination = ?
              AND timestamp > datetime('now', ? || ' minutes')
            ORDER BY timestamp DESC
            LIMIT ?
            """,
            (destination, f"-{window_minutes}", peer_limit),
            fetch="all",
        ) or []

        nodes: list[dict[str, Any]] = []
        edges: list[dict[str, Any]] = []
        seen_nodes: set[str] = set()

        agent_node = f"agent:{agent_id}"
        self._add_node(nodes, seen_nodes, agent_node, "agent", label=agent_id, focus=True)

        chain_totals: dict[str, float] = defaultdict(float)
        destination_counts: dict[str, int] = defaultdict(int)

        for row in recent_flows:
            row_chain = str(row["chain"] or chain or "arc").lower()
            row_destination = str(row["destination"] or "")
            row_amount = float(row["amount_usdc"] or 0.0)
            chain_node = f"chain:{row_chain}"
            destination_node = f"dest:{row_destination.lower()}"

            self._add_node(
                nodes,
                seen_nodes,
                chain_node,
                "chain",
                label=row_chain,
            )
            self._add_node(
                nodes,
                seen_nodes,
                destination_node,
                "destination",
                label=row_destination[:18],
                focus=row_destination.lower() == destination.lower(),
            )

            chain_totals[row_chain] += row_amount
            destination_counts[row_destination.lower()] += 1

            edges.append(
                {
                    "source": agent_node,
                    "target": chain_node,
                    "kind": "uses_chain",
                    "amount_usdc": round(row_amount, 6),
                    "timestamp": row["timestamp"],
                }
            )
            edges.append(
                {
                    "source": chain_node,
                    "target": destination_node,
                    "kind": "transfer",
                    "amount_usdc": round(row_amount, 6),
                    "timestamp": row["timestamp"],
                }
            )

        focus_stats = self._focus_destination_stats(destination, recent_flows, peer_decisions)

        for row in peer_decisions:
            peer_agent = str(row["agent_id"] or "")
            if not peer_agent or peer_agent == agent_id:
                continue
            peer_node = f"agent:{peer_agent}"
            self._add_node(
                nodes,
                seen_nodes,
                peer_node,
                "peer_agent",
                label=peer_agent,
            )
            edges.append(
                {
                    "source": peer_node,
                    "target": f"dest:{destination.lower()}",
                    "kind": "peer_transfer",
                    "amount_usdc": round(float(row["amount_usdc"] or 0.0), 6),
                    "decision": row["decision"],
                    "timestamp": row["timestamp"],
                }
            )

        dominant_chain = chain
        if chain_totals:
            dominant_chain = max(chain_totals, key=chain_totals.get)

        total_amount = round(
            sum(float(row["amount_usdc"] or 0.0) for row in recent_flows), 6
        )
        summary = {
            "tx_count": len(recent_flows),
            "total_amount": total_amount,
            "current_amount_usdc": round(float(amount_usdc or 0.0), 6),
            "unique_destinations": len(destination_counts),
            "chain_count": len(chain_totals),
            "chains": sorted(chain_totals.keys()),
            "focus_destination": destination,
            "focus_tx_count": focus_stats["tx_count"],
            "focus_total_amount": focus_stats["total_amount"],
            "focus_chain_count": focus_stats["chain_count"],
            "focus_unique_peer_senders": focus_stats["unique_peer_senders"],
            "dominant_chain": dominant_chain,
            "max_destination_tx_count": max(destination_counts.values(), default=0),
        }

        pattern, confidence, risk_delta, evidence = self._infer_pattern(summary, chain)
        summary.update(
            {
                "heuristic_pattern": pattern,
                "heuristic_confidence": confidence,
                "heuristic_risk_delta": risk_delta,
                "heuristic_evidence": evidence,
            }
        )

        return {
            "agent_id": agent_id,
            "nodes": nodes,
            "edges": edges,
            "summary": summary,
            "prompt_context": {
                "focus_chain": chain,
                "focus_destination": destination,
                "summary": summary,
            },
        }

    async def build_for_agent(
        self,
        agent_id: str,
        destination: str = "",
        chain: str = "arc",
        amount_usdc: float = 0.0,
    ) -> dict[str, Any]:
        return await self.build_for_action(
            agent_id=agent_id,
            destination=destination,
            chain=chain,
            amount_usdc=amount_usdc,
        )


graph_builder_service = GraphBuilderService()
