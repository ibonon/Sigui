import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from modules.memory import memory


async def run():
    await memory.initialize()
    for table in ["decisions", "attacks", "patterns", "agents", "treasury_log", "episodic_memory", "policy_updates"]:
        await memory._db.execute(f"DELETE FROM {table}")
    await memory._db.commit()
    await memory.close()
    print("Demo DB reset complete.")


if __name__ == "__main__":
    asyncio.run(run())

