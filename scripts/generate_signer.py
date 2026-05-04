from eth_account import Account
import secrets
import os

account = Account.create(secrets.token_hex(32))
print(f"Address: {account.address}")
print(f"PrivateKey: {account.key.hex()}")

env_path = ".env"
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "ARC_SIGNER_PRIVATE_KEY" in content:
        import re
        content = re.sub(r"^ARC_SIGNER_PRIVATE_KEY=.*$", f"ARC_SIGNER_PRIVATE_KEY={account.key.hex()}", content, flags=re.MULTILINE)
        content = re.sub(r"^ARC_SIGNER_ADDRESS=.*$", f"ARC_SIGNER_ADDRESS={account.address}", content, flags=re.MULTILINE)
    else:
        content += f"\nARC_SIGNER_PRIVATE_KEY={account.key.hex()}\nARC_SIGNER_ADDRESS={account.address}\n"
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.write(content)
