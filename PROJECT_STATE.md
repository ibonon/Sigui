# Sigui Project Handover - Technical Context

## 1. Project Identity
- **Name**: Sigui (Multichain DePIN Security Oracle)
- **Objective**: Autonomous security layer for the Agentic Economy, utilizing VLM (Vision-Language Models) to detect on-chain threat topologies.
- **Hardware Stack**: AMD MI300X (GPU Droplet at 165.245.134.58).
- **Core Standard**: ERC-8259 (AI Agent Identity & Threat Registry).

## 2. Current Status (May 9, 2026)
- **Data Pipeline**: 1.87 million real transactions collected from Ethereum, Arbitrum, and Polygon.
- **Generation Phase**: Currently generating 1,000,000 visual graphs on the AMD server (20 cores).
- **Processing Speed**: ~225 iterations/sec (Expected completion: ~1.2 hours).
- **Storage**: ~624GB available on server; dataset expected to take ~100GB.
- **Environment**: Python 3.12 virtual environment at `~/venv_sigui`.

## 3. Infrastructure Details (AMD Droplet)
- **IP**: 165.245.134.58
- **OS**: Ubuntu 24.04 (Noble)
- **Tools Installed**:
  - `LLaMA-Factory` (cloned and installed in `~/LLaMA-Factory`).
  - `networkx`, `matplotlib` (Agg backend), `tqdm`.
  - `tmux` session `data_gen` is running the generation.

## 4. Next Technical Steps (Post-Generation)
1. **Prepare Training Dataset**: Update `LLaMA-Factory/data/dataset_info.json` to include the generated `qwen2_vl_real_data.jsonl`.
2. **Launch Fine-Tuning**: Execute `llamafactory-cli train train_sigui.yaml` using the AMD MI300X.
3. **Model Weights**: The LoRA weights will be saved in `saves/sigui-v2-1m/lora/sft`.
4. **Integration**: Connect the `DecisionEngine` in the Sigui Dashboard to the new vLLM endpoint serving the fine-tuned model.

## 5. Critical Files
- `scripts/generate_v2_real_data_mp.py`: Optimized multi-processing graph generator.
- `datasets/real_raw/transactions_real.jsonl`: The raw transaction source (630MB).
- `.env`: Contains the IP endpoints and API keys.
