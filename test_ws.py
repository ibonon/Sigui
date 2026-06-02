import asyncio
import websockets

async def test():
    try:
        # Some versions of websockets use `headers` instead of `extra_headers`
        async with websockets.connect('ws://127.0.0.1:8000/ws/live', origin='http://localhost:3001') as ws:
            print('Connected to ws://127.0.0.1:8000/ws/live!')
            msg = await asyncio.wait_for(ws.recv(), timeout=2.0)
            print('Received:', msg)
    except Exception as e:
        print('Error:', e)

asyncio.run(test())
