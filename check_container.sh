#!/bin/bash
# Container içinde çalıştırılacak kontrol scripti

echo "=== Container Health Check ==="
echo ""

# 1. Python ile health check
echo "1. Health Check Test:"
python3 -c "
import urllib.request
import json
try:
    response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
    data = json.loads(response.read().decode())
    print(f'   ✓ Health check OK: {data}')
except Exception as e:
    print(f'   ✗ Health check FAILED: {e}')
    exit(1)
"

# 2. Uvicorn process kontrolü
echo ""
echo "2. Uvicorn Process Check:"
python3 -c "
import subprocess
result = subprocess.run(['pgrep', '-f', 'uvicorn'], capture_output=True, text=True)
if result.returncode == 0:
    pids = result.stdout.strip().split('\n')
    print(f'   ✓ Uvicorn running (PIDs: {pids})')
else:
    print('   ✗ Uvicorn not found')
    exit(1)
"

# 3. Port dinleme kontrolü
echo ""
echo "3. Port 8000 Listening Check:"
python3 -c "
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 8000))
sock.close()
if result == 0:
    print('   ✓ Port 8000 is listening')
else:
    print('   ✗ Port 8000 is not listening')
    exit(1)
"

# 4. Database bağlantı kontrolü
echo ""
echo "4. Database Connection Check:"
python3 -c "
try:
    from app.core.database import engine
    conn = engine.connect()
    conn.close()
    print('   ✓ Database connection OK')
except Exception as e:
    print(f'   ⚠ Database connection: {e}')
"

echo ""
echo "=== Check Complete ==="











