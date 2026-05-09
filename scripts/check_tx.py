import sqlite3

conn = sqlite3.connect('db/sigui.db')
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "SELECT arc_tx_hash, decision, timestamp FROM decisions WHERE arc_tx_hash IS NOT NULL AND arc_tx_hash != '' ORDER BY timestamp DESC LIMIT 30"
).fetchall()

print(f"Total: {len(rows)} decisions with a tx hash")
for r in rows:
    print(dict(r))

conn.close()
