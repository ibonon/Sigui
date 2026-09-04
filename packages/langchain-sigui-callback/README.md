# langchain-sigui-callback

Sigui Security Oracle Callback Handler for **LangChain** and **LangGraph** autonomous agents.

Pre-evaluates blockchain transactions, contract interactions, and financial tool invocations against fine-tuned vision models (Qwen2-VL-7B on AMD MI300X), Groth16 ZK proofs, and dynamic threat blacklists.

## Installation

```bash
pip install langchain-sigui-callback
```

## Quick Start

```python
from langchain_sigui_callback import SiguiSecurityCallbackHandler
from langchain.agents import initialize_agent

sigui_handler = SiguiSecurityCallbackHandler(
    api_key="your_sigui_key",
    endpoint="http://127.0.0.1:8000",
    fail_on_block=True
)

agent = initialize_agent(
    tools=tools,
    llm=llm,
    callbacks=[sigui_handler]
)
```

## How It Works

1. Intercepts tool calls starting with `transfer`, `swap`, or `pay`.
2. Queries Sigui Oracle `/v2/evaluate?zk=true`.
3. If threat pattern (e.g. `DRAIN_STAR`, `MIXING_CHAIN`) is detected with high risk score, raises `ValueError` to block transaction before execution.
