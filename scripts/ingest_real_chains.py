"""
Ingest real on-chain data across several blockchains and export normalized JSONL.

Objectif:
  - recuperer un maximum de donnees avec des API gratuites
  - reprendre un run interrompu sans perdre les lignes deja telechargees
  - s'arreter proprement quand un quota gratuit ou un rate limit bloque la suite

Chaines prises en charge:
  - ethereum
  - polygon
  - arbitrum
  - base
  - optimism
  - solana

Exemples:
  python scripts/ingest_real_chains.py --out datasets/real_raw
  python scripts/ingest_real_chains.py --chains ethereum,polygon,solana --out datasets/real_raw
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ETHERSCAN_BASE = "https://api.etherscan.io/v2/api"
SOLANA_RPC_DEFAULT = "https://api.mainnet-beta.solana.com"
SOLANA_USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
STATE_FILE_NAME = "ingest_state.json"
SUMMARY_FILE_NAME = "ingest_summary.json"
OUTPUT_FILE_NAME = "transactions_real.jsonl"
DEFAULT_CHAINS = ["ethereum", "polygon", "arbitrum", "base", "optimism", "solana"]


@dataclass(frozen=True)
class EvmChainDefinition:
    name: str
    chain_id: str
    usdc_contract: str
    default_addresses_file: str = "data/seed_evm_common.txt"


EVM_CHAINS: dict[str, EvmChainDefinition] = {
    "ethereum": EvmChainDefinition(
        name="ethereum",
        chain_id="1",
        usdc_contract="0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48",
        default_addresses_file="data/seed_eth.txt",
    ),
    "polygon": EvmChainDefinition(
        name="polygon",
        chain_id="137",
        usdc_contract="0x3c499c542cef5e3811e1192ce70d8cc03d5c3359",
    ),
    "arbitrum": EvmChainDefinition(
        name="arbitrum",
        chain_id="42161",
        usdc_contract="0xaf88d065e77c8cc2239327c5edb3a432268e5831",
        default_addresses_file="data/seed_arbitrum.txt",
    ),
    "base": EvmChainDefinition(
        name="base",
        chain_id="8453",
        usdc_contract="0x833589fcd6edb6e08f4c7c32d4f71b54bda02913",
        default_addresses_file="data/seed_base.txt",
    ),
    "optimism": EvmChainDefinition(
        name="optimism",
        chain_id="10",
        usdc_contract="0x0b2c639c533813f4aa9d7837caf62653d097ff85",
        default_addresses_file="data/seed_optimism.txt",
    ),
}


@dataclass
class IngestConfig:
    out_dir: Path
    active_chains: list[str]
    evm_addresses_by_chain: dict[str, list[str]]
    sol_addresses: list[str]
    evm_max_txs_per_address: int
    evm_page_size: int
    evm_max_pages_per_address: int
    evm_request_delay_s: float
    sol_max_signatures_per_address: int
    sol_signature_page_size: int
    sol_max_pages_per_address: int
    solana_rpc_url: str
    sol_request_delay_s: float
    resume: bool = True
    timeout_s: float = 20.0


class JsonlSink:
    def __init__(self, path: Path, resume: bool):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.seen_keys: set[str] = set()
        mode = "a" if resume and path.exists() else "w"
        if resume and path.exists():
            self._load_existing_keys()
        self._handle = path.open(mode, encoding="utf-8")

    def _load_existing_keys(self):
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = _row_key(str(obj.get("chain", "")), str(obj.get("tx_hash", "")))
                if key:
                    self.seen_keys.add(key)

    def append(self, row: dict[str, Any]) -> bool:
        key = _row_key(str(row.get("chain", "")), str(row.get("tx_hash", "")))
        if not key or key in self.seen_keys:
            return False
        self._handle.write(json.dumps(row, ensure_ascii=True) + "\n")
        self._handle.flush()
        self.seen_keys.add(key)
        return True

    def close(self):
        self._handle.close()


def _row_key(chain: str, tx_hash: str) -> str:
    chain = chain.strip().lower()
    tx_hash = tx_hash.strip().lower()
    if not chain or not tx_hash:
        return ""
    return f"{chain}:{tx_hash}"


def _parse_addresses(args_value: str, file_path: str | None) -> list[str]:
    items: list[str] = []
    if args_value:
        items.extend([x.strip() for x in args_value.split(",") if x.strip()])
    if file_path:
        p = _resolve_input_path(file_path)
        if p.exists():
            items.extend(
                [
                    ln.strip()
                    for ln in p.read_text(encoding="utf-8").splitlines()
                    if ln.strip() and not ln.strip().startswith("#")
                ]
            )
    seen = set()
    out = []
    for item in items:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _resolve_input_path(path_str: str) -> Path:
    candidate = Path(path_str)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate
    return PROJECT_ROOT / candidate


def _merge_address_lists(*address_lists: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for items in address_lists:
        for item in items:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


def _parse_chain_list(raw_value: str) -> list[str]:
    chains = [item.strip().lower() for item in raw_value.split(",") if item.strip()]
    out: list[str] = []
    seen: set[str] = set()
    supported = set(EVM_CHAINS) | {"solana"}
    for chain in chains:
        if chain not in supported:
            raise SystemExit(
                f"Unsupported chain '{chain}'. Supported chains: {', '.join(sorted(supported))}"
            )
        if chain not in seen:
            seen.add(chain)
            out.append(chain)
    return out


def _default_state() -> dict[str, Any]:
    return {"evm": {}, "solana": {}}


def _default_existing_file(path_str: str) -> str | None:
    path = _resolve_input_path(path_str)
    if path.exists():
        return str(path)
    return None


def _build_evm_addresses_by_chain(args: argparse.Namespace) -> dict[str, list[str]]:
    generic_file = args.evm_addresses_file or _default_existing_file("data/seed_evm_common.txt")
    generic_addresses = _parse_addresses(args.evm_addresses, generic_file)
    chain_specific_raw = {
        "ethereum": (args.ethereum_addresses or args.eth_addresses, args.ethereum_addresses_file or args.eth_addresses_file or _default_existing_file("data/seed_eth.txt")),
        "polygon": (args.polygon_addresses, args.polygon_addresses_file),
        "arbitrum": (args.arbitrum_addresses, args.arbitrum_addresses_file),
        "base": (args.base_addresses, args.base_addresses_file),
        "optimism": (args.optimism_addresses, args.optimism_addresses_file),
    }
    addresses_by_chain: dict[str, list[str]] = {}
    for chain_name, chain_def in EVM_CHAINS.items():
        inline_value, file_value = chain_specific_raw[chain_name]
        default_file = file_value or _default_existing_file(chain_def.default_addresses_file)
        chain_specific = _parse_addresses(inline_value, default_file)
        if chain_name == "ethereum":
            addresses_by_chain[chain_name] = _merge_address_lists(chain_specific, generic_addresses)
        else:
            addresses_by_chain[chain_name] = _merge_address_lists(generic_addresses, chain_specific)
    return addresses_by_chain


def _load_state(path: Path, resume: bool) -> dict[str, Any]:
    if resume and path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                data.setdefault("evm", {})
                data.setdefault("solana", {})
                return data
        except Exception:
            pass
    return _default_state()


def _save_json(path: Path, obj: Any):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def _retry_delay_s(attempt: int, exc: Exception) -> float:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        retry_after = exc.response.headers.get("Retry-After")
        if retry_after:
            try:
                return max(1.0, float(retry_after))
            except ValueError:
                pass
    return min(60.0, float(2**attempt))


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
        return exc.response.status_code in {408, 425, 429, 500, 502, 503, 504}
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def _looks_like_quota_message(text: str) -> bool:
    lowered = text.lower()
    patterns = (
        "rate limit",
        "max rate limit",
        "too many requests",
        "quota",
        "daily limit",
        "limit reached",
        "usage cap",
    )
    return any(pattern in lowered for pattern in patterns)


def _etherscan_payload_error(payload: dict[str, Any]) -> str:
    result = payload.get("result")
    message = str(payload.get("message", "") or "")
    if isinstance(result, str):
        text = result.strip()
        if text and (payload.get("status") == "0" or _looks_like_quota_message(text)):
            return f"{message} {text}".strip()
    if payload.get("status") == "0" and message and message.upper() != "NO TRANSACTIONS FOUND":
        return message
    return ""


async def _get_json(
    client: httpx.AsyncClient,
    url: str,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    last_err: Exception | None = None
    for attempt in range(6):
        try:
            if json_body is not None:
                response = await client.post(url, json=json_body)
            else:
                response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            last_err = exc
            if attempt == 5 or not _is_retryable(exc):
                break
            await asyncio.sleep(_retry_delay_s(attempt, exc))
    raise RuntimeError(f"Request failed after retries: {url} ({last_err})")


def _to_float(raw: str | int | float, decimals: int) -> float:
    try:
        return float(raw) / (10 ** decimals)
    except Exception:
        return 0.0


def _normalize_evm_tx(chain_name: str, tx: dict[str, Any]) -> dict[str, Any] | None:
    tx_hash = str(tx.get("hash", "")).strip()
    if not tx_hash:
        return None
    if str(tx.get("tokenSymbol", "")).upper() != "USDC":
        return None
    decimals = int(tx.get("tokenDecimal", "6") or "6")
    amount = _to_float(tx.get("value", "0"), decimals)
    return {
        "chain": chain_name,
        "tx_hash": tx_hash,
        "from": str(tx.get("from", "")).lower(),
        "to": str(tx.get("to", "")).lower(),
        "amount_usdc": round(amount, 6),
        "timestamp": int(tx.get("timeStamp", 0) or 0),
        "block_number": int(tx.get("blockNumber", 0) or 0),
        "token": "USDC",
        "source": "etherscan_tokentx",
    }


def _extract_solana_usdc_amount(tx_obj: dict[str, Any]) -> float:
    try:
        meta = tx_obj.get("meta") or {}
        pre = meta.get("preTokenBalances") or []
        post = meta.get("postTokenBalances") or []
        pre_total = 0.0
        post_total = 0.0
        for item in pre:
            if item.get("mint") == SOLANA_USDC_MINT:
                amount = ((item.get("uiTokenAmount") or {}).get("uiAmount")) or 0.0
                pre_total += float(amount)
        for item in post:
            if item.get("mint") == SOLANA_USDC_MINT:
                amount = ((item.get("uiTokenAmount") or {}).get("uiAmount")) or 0.0
                post_total += float(amount)
        return round(abs(post_total - pre_total), 6)
    except Exception:
        return 0.0


def _normalize_solana_tx(address: str, signature: str, block_time: int, tx_obj: dict[str, Any]) -> dict[str, Any] | None:
    if not signature:
        return None
    account_keys = (((tx_obj.get("transaction") or {}).get("message") or {}).get("accountKeys") or [])
    src = str(account_keys[0].get("pubkey") if account_keys and isinstance(account_keys[0], dict) else address)
    dst = str(account_keys[1].get("pubkey") if len(account_keys) > 1 and isinstance(account_keys[1], dict) else "")
    return {
        "chain": "solana",
        "tx_hash": signature,
        "from": src,
        "to": dst,
        "amount_usdc": _extract_solana_usdc_amount(tx_obj),
        "timestamp": int(block_time or 0),
        "block_number": int(tx_obj.get("slot") or 0),
        "token": "USDC",
        "source": "solana_rpc",
    }


async def ingest_evm_chain(
    client: httpx.AsyncClient,
    cfg: IngestConfig,
    sink: JsonlSink,
    state: dict[str, Any],
    state_path: Path,
    api_key: str,
    chain_def: EvmChainDefinition,
    addresses: list[str],
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "chain": chain_def.name,
        "rows_added": 0,
        "requests": 0,
        "addresses_completed": 0,
        "quota_exhausted": False,
        "stop_reason": "completed",
    }
    if not addresses:
        stats["stop_reason"] = "no_addresses"
        return stats
    if not api_key:
        stats["stop_reason"] = "missing_api_key"
        print(f"[WARN] ETHERSCAN_API_KEY missing -> skipping {chain_def.name} ingestion")
        return stats

    evm_state = state.setdefault("evm", {})
    chain_state = evm_state.setdefault(chain_def.name, {})
    for address in addresses:
        addr_state = chain_state.setdefault(
            address,
            {
                "next_page": 1,
                "pages_completed": 0,
                "scanned_items": 0,
                "rows_added": 0,
                "status": "pending",
            },
        )
        if addr_state.get("status") == "done":
            stats["addresses_completed"] += 1
            continue

        next_page = max(1, int(addr_state.get("next_page", 1)))
        while (
            int(addr_state.get("scanned_items", 0)) < cfg.evm_max_txs_per_address
            and int(addr_state.get("pages_completed", 0)) < cfg.evm_max_pages_per_address
        ):
            remaining = cfg.evm_max_txs_per_address - int(addr_state.get("scanned_items", 0))
            page_size = max(1, min(cfg.evm_page_size, remaining))
            params = {
                "chainid": chain_def.chain_id,
                "module": "account",
                "action": "tokentx",
                "contractaddress": chain_def.usdc_contract,
                "address": address,
                "page": str(next_page),
                "offset": str(page_size),
                "sort": "desc",
                "apikey": api_key,
            }
            try:
                data = await _get_json(client, ETHERSCAN_BASE, params=params)
            except RuntimeError as exc:
                msg = str(exc)
                if _looks_like_quota_message(msg):
                    addr_state["status"] = "quota_exhausted"
                    stats["quota_exhausted"] = True
                    stats["stop_reason"] = "quota_exhausted"
                    _save_json(state_path, state)
                    return stats
                addr_state["status"] = "request_error"
                addr_state["last_error"] = msg
                _save_json(state_path, state)
                break

            stats["requests"] += 1
            payload_error = _etherscan_payload_error(data)
            if payload_error:
                if _looks_like_quota_message(payload_error):
                    addr_state["status"] = "quota_exhausted"
                    stats["quota_exhausted"] = True
                    stats["stop_reason"] = "quota_exhausted"
                    _save_json(state_path, state)
                    return stats
                addr_state["status"] = "api_error"
                addr_state["last_error"] = payload_error
                _save_json(state_path, state)
                break

            txs = data.get("result") or []
            if not isinstance(txs, list) or not txs:
                addr_state["status"] = "done"
                _save_json(state_path, state)
                stats["addresses_completed"] += 1
                break

            page_rows_added = 0
            for tx in txs:
                row = _normalize_evm_tx(chain_def.name, tx)
                if row and sink.append(row):
                    page_rows_added += 1

            addr_state["rows_added"] = int(addr_state.get("rows_added", 0)) + page_rows_added
            addr_state["scanned_items"] = int(addr_state.get("scanned_items", 0)) + len(txs)
            addr_state["pages_completed"] = int(addr_state.get("pages_completed", 0)) + 1
            stats["rows_added"] += page_rows_added

            if len(txs) < page_size:
                addr_state["status"] = "done"
                _save_json(state_path, state)
                stats["addresses_completed"] += 1
                break

            next_page += 1
            addr_state["next_page"] = next_page
            addr_state["status"] = "running"
            _save_json(state_path, state)
            if cfg.evm_request_delay_s > 0:
                await asyncio.sleep(cfg.evm_request_delay_s)
        else:
            if int(addr_state.get("scanned_items", 0)) >= cfg.evm_max_txs_per_address:
                addr_state["status"] = "max_items_reached"
            elif int(addr_state.get("pages_completed", 0)) >= cfg.evm_max_pages_per_address:
                addr_state["status"] = "max_pages_reached"
            _save_json(state_path, state)

    return stats


async def ingest_evm_chains(
    client: httpx.AsyncClient,
    cfg: IngestConfig,
    sink: JsonlSink,
    state: dict[str, Any],
    state_path: Path,
    api_key: str,
) -> dict[str, Any]:
    stats_by_chain: dict[str, Any] = {}
    evm_quota_exhausted = False
    for chain_name in cfg.active_chains:
        if chain_name not in EVM_CHAINS:
            continue
        chain_def = EVM_CHAINS[chain_name]
        if evm_quota_exhausted:
            stats_by_chain[chain_name] = {
                "chain": chain_name,
                "rows_added": 0,
                "requests": 0,
                "addresses_completed": 0,
                "quota_exhausted": True,
                "stop_reason": "skipped_after_evm_quota_exhausted",
            }
            continue
        chain_stats = await ingest_evm_chain(
            client=client,
            cfg=cfg,
            sink=sink,
            state=state,
            state_path=state_path,
            api_key=api_key,
            chain_def=chain_def,
            addresses=cfg.evm_addresses_by_chain.get(chain_name, []),
        )
        stats_by_chain[chain_name] = chain_stats
        if chain_stats.get("quota_exhausted"):
            evm_quota_exhausted = True
    return stats_by_chain


async def ingest_solana(
    client: httpx.AsyncClient,
    cfg: IngestConfig,
    sink: JsonlSink,
    state: dict[str, Any],
    state_path: Path,
) -> dict[str, Any]:
    stats: dict[str, Any] = {
        "chain": "solana",
        "rows_added": 0,
        "requests": 0,
        "addresses_completed": 0,
        "quota_exhausted": False,
        "stop_reason": "completed",
    }
    if "solana" not in cfg.active_chains:
        stats["stop_reason"] = "disabled"
        return stats
    if not cfg.sol_addresses:
        stats["stop_reason"] = "no_addresses"
        return stats
    sol_state = state.setdefault("solana", {})
    for address in cfg.sol_addresses:
        addr_state = sol_state.setdefault(
            address,
            {
                "before": None,
                "pages_completed": 0,
                "scanned_signatures": 0,
                "rows_added": 0,
                "status": "pending",
            },
        )
        if addr_state.get("status") == "done":
            stats["addresses_completed"] += 1
            continue

        while (
            int(addr_state.get("scanned_signatures", 0)) < cfg.sol_max_signatures_per_address
            and int(addr_state.get("pages_completed", 0)) < cfg.sol_max_pages_per_address
        ):
            remaining = cfg.sol_max_signatures_per_address - int(addr_state.get("scanned_signatures", 0))
            page_size = max(1, min(cfg.sol_signature_page_size, remaining))
            request_params: dict[str, Any] = {"limit": page_size}
            if addr_state.get("before"):
                request_params["before"] = addr_state["before"]
            sig_req = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getSignaturesForAddress",
                "params": [address, request_params],
            }
            try:
                sig_data = await _get_json(client, cfg.solana_rpc_url, json_body=sig_req)
            except RuntimeError as exc:
                msg = str(exc)
                if _looks_like_quota_message(msg):
                    addr_state["status"] = "quota_exhausted"
                    stats["quota_exhausted"] = True
                    stats["stop_reason"] = "quota_exhausted"
                    _save_json(state_path, state)
                    return stats
                addr_state["status"] = "request_error"
                addr_state["last_error"] = msg
                _save_json(state_path, state)
                break

            stats["requests"] += 1
            sigs = sig_data.get("result") or []
            if not isinstance(sigs, list) or not sigs:
                addr_state["status"] = "done"
                _save_json(state_path, state)
                stats["addresses_completed"] += 1
                break

            page_rows_added = 0
            for item in sigs:
                signature = str(item.get("signature", "")).strip()
                block_time = int(item.get("blockTime") or 0)
                if not signature:
                    continue
                tx_req = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "getTransaction",
                    "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}],
                }
                try:
                    tx_data = await _get_json(client, cfg.solana_rpc_url, json_body=tx_req)
                except RuntimeError as exc:
                    msg = str(exc)
                    if _looks_like_quota_message(msg):
                        addr_state["status"] = "quota_exhausted"
                        stats["quota_exhausted"] = True
                        stats["stop_reason"] = "quota_exhausted"
                        _save_json(state_path, state)
                        return stats
                    print(f"[WARN] Solana transaction skipped: {signature} ({msg})")
                    continue

                stats["requests"] += 1
                tx_obj = tx_data.get("result") or {}
                row = _normalize_solana_tx(address, signature, block_time, tx_obj)
                if row and sink.append(row):
                    page_rows_added += 1
                if cfg.sol_request_delay_s > 0:
                    await asyncio.sleep(cfg.sol_request_delay_s)

            addr_state["rows_added"] = int(addr_state.get("rows_added", 0)) + page_rows_added
            addr_state["scanned_signatures"] = int(addr_state.get("scanned_signatures", 0)) + len(sigs)
            addr_state["pages_completed"] = int(addr_state.get("pages_completed", 0)) + 1
            addr_state["before"] = str(sigs[-1].get("signature", "") or "")
            addr_state["status"] = "running"
            stats["rows_added"] += page_rows_added
            _save_json(state_path, state)

            if len(sigs) < page_size:
                addr_state["status"] = "done"
                _save_json(state_path, state)
                stats["addresses_completed"] += 1
                break

        else:
            if int(addr_state.get("scanned_signatures", 0)) >= cfg.sol_max_signatures_per_address:
                addr_state["status"] = "max_items_reached"
            elif int(addr_state.get("pages_completed", 0)) >= cfg.sol_max_pages_per_address:
                addr_state["status"] = "max_pages_reached"
            _save_json(state_path, state)

    return stats


async def run(cfg: IngestConfig):
    out_path = cfg.out_dir / OUTPUT_FILE_NAME
    state_path = cfg.out_dir / STATE_FILE_NAME
    summary_path = cfg.out_dir / SUMMARY_FILE_NAME
    state = _load_state(state_path, resume=cfg.resume)
    sink = JsonlSink(out_path, resume=cfg.resume)

    if "solana" in cfg.active_chains and cfg.sol_addresses and cfg.solana_rpc_url == SOLANA_RPC_DEFAULT:
        print(
            "[INFO] Public Solana RPC detecte. Le script va accumuler les donnees "
            "jusqu'au rate limit puis enregistrer un etat de reprise."
        )

    try:
        async with httpx.AsyncClient(timeout=cfg.timeout_s) as client:
            evm_stats = await ingest_evm_chains(
                client=client,
                cfg=cfg,
                sink=sink,
                state=state,
                state_path=state_path,
                api_key=os.getenv("ETHERSCAN_API_KEY", ""),
            )
            sol_stats = await ingest_solana(
                client=client,
                cfg=cfg,
                sink=sink,
                state=state,
                state_path=state_path,
            )
    finally:
        sink.close()

    summary = {
        "output_file": str(out_path),
        "state_file": str(state_path),
        "resume_enabled": cfg.resume,
        "active_chains": cfg.active_chains,
        "rows_total_in_file": len(sink.seen_keys),
        "evm": evm_stats,
        "solana": sol_stats,
    }
    _save_json(summary_path, summary)
    print(f"Wrote data incrementally to {out_path}")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=str, default="datasets/real_raw")
    parser.add_argument("--chains", type=str, default=",".join(DEFAULT_CHAINS))
    parser.add_argument("--evm-addresses", type=str, default="")
    parser.add_argument("--evm-addresses-file", type=str, default="")
    parser.add_argument("--eth-addresses", type=str, default="")
    parser.add_argument("--eth-addresses-file", type=str, default="")
    parser.add_argument("--ethereum-addresses", type=str, default="")
    parser.add_argument("--ethereum-addresses-file", type=str, default="")
    parser.add_argument("--polygon-addresses", type=str, default="")
    parser.add_argument("--polygon-addresses-file", type=str, default="")
    parser.add_argument("--arbitrum-addresses", type=str, default="")
    parser.add_argument("--arbitrum-addresses-file", type=str, default="")
    parser.add_argument("--base-addresses", type=str, default="")
    parser.add_argument("--base-addresses-file", type=str, default="")
    parser.add_argument("--optimism-addresses", type=str, default="")
    parser.add_argument("--optimism-addresses-file", type=str, default="")
    parser.add_argument("--sol-addresses", type=str, default="")
    parser.add_argument("--sol-addresses-file", type=str, default="")
    parser.add_argument("--evm-max-tx", type=int, default=20000)
    parser.add_argument("--evm-page-size", type=int, default=1000)
    parser.add_argument("--evm-max-pages", type=int, default=200)
    parser.add_argument("--evm-request-delay", type=float, default=0.25)
    parser.add_argument("--eth-max-tx", type=int, default=0)
    parser.add_argument("--eth-page-size", type=int, default=0)
    parser.add_argument("--eth-max-pages", type=int, default=0)
    parser.add_argument("--eth-request-delay", type=float, default=-1.0)
    parser.add_argument("--sol-max-sigs", type=int, default=2000)
    parser.add_argument("--sol-page-size", type=int, default=100)
    parser.add_argument("--sol-max-pages", type=int, default=100)
    parser.add_argument("--sol-request-delay", type=float, default=0.35)
    parser.add_argument("--solana-rpc-url", type=str, default=SOLANA_RPC_DEFAULT)
    parser.add_argument("--resume", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()

    active_chains = _parse_chain_list(args.chains)
    evm_addresses_by_chain = _build_evm_addresses_by_chain(args)
    sol_addresses_file = args.sol_addresses_file or _default_existing_file("data/seed_solana.txt")
    sol_addresses = _parse_addresses(args.sol_addresses, sol_addresses_file)
    evm_max_tx = args.eth_max_tx if args.eth_max_tx > 0 else args.evm_max_tx
    evm_page_size = args.eth_page_size if args.eth_page_size > 0 else args.evm_page_size
    evm_max_pages = args.eth_max_pages if args.eth_max_pages > 0 else args.evm_max_pages
    evm_request_delay = args.eth_request_delay if args.eth_request_delay >= 0 else args.evm_request_delay

    cfg = IngestConfig(
        out_dir=Path(args.out),
        active_chains=active_chains,
        evm_addresses_by_chain=evm_addresses_by_chain,
        sol_addresses=sol_addresses,
        evm_max_txs_per_address=max(1, evm_max_tx),
        evm_page_size=max(1, evm_page_size),
        evm_max_pages_per_address=max(1, evm_max_pages),
        evm_request_delay_s=max(0.0, evm_request_delay),
        sol_max_signatures_per_address=max(1, args.sol_max_sigs),
        sol_signature_page_size=max(1, args.sol_page_size),
        sol_max_pages_per_address=max(1, args.sol_max_pages),
        solana_rpc_url=args.solana_rpc_url,
        sol_request_delay_s=max(0.0, args.sol_request_delay),
        resume=bool(args.resume),
    )
    has_any_evm_addresses = any(
        cfg.evm_addresses_by_chain.get(chain_name)
        for chain_name in cfg.active_chains
        if chain_name in EVM_CHAINS
    )
    has_any_requested_addresses = has_any_evm_addresses or (
        "solana" in cfg.active_chains and bool(cfg.sol_addresses)
    )
    if not has_any_requested_addresses:
        raise SystemExit(
            "Provide at least one address for an active chain via the EVM/Solana address flags or seed files."
        )
    asyncio.run(run(cfg))


if __name__ == "__main__":
    main()
