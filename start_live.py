from sigui.local import start_mock_server
import time

print("Starting Sigui Live Mock Server on ws://localhost:8000/ws/live")
server = start_mock_server(port=8000)

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Shutting down...")
    server.stop()
