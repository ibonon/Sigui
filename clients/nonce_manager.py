
import asyncio

# Global lock for EVM transaction nonces to prevent collisions
# when multiple clients use the same signer address concurrently.
nonce_lock = asyncio.Lock()
