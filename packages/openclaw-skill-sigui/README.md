# openclaw-skill-sigui

Sigui Protocol DePIN AI Security Oracle Skill for **OpenClaw** Autonomous Agents.

## Overview
This skill integrates Sigui Security Oracle into OpenClaw pipelines, preventing agent actions from executing on suspicious contract addresses, Drain Stars, or Mixer Chains.

## Installation

```bash
pip install openclaw-skill-sigui
```

## Usage

```python
from openclaw_skill_sigui import SiguiSecuritySkill

skill = SiguiSecuritySkill()
audit = skill.audit_transaction("0x742d35Cc6634C0532925a3b844Bc454e4438f44e", amount_usdc=500.0)

if not audit["allowed"]:
    print(f"Transaction blocked: {audit['reason']}")
```
