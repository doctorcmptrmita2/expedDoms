#!/bin/bash
# Database connection check script

echo "=== Database Connection Check ==="
echo ""

# 1. Check DATABASE_URL environment variable
echo "1. DATABASE_URL Environment Variable:"
python3 -c "
import os
db_url = os.environ.get('DATABASE_URL', 'NOT SET')
print(f'   DATABASE_URL: {db_url[:80]}...' if len(db_url) > 80 else f'   DATABASE_URL: {db_url}')
"

# 2. Check DATABASE_URL from settings
echo ""
echo "2. DATABASE_URL from Settings:"
python3 -c "
try:
    from app.core.config import get_settings
    s = get_settings()
    db_url = s.DATABASE_URL
    print(f'   DATABASE_URL: {db_url[:80]}...' if len(db_url) > 80 else f'   DATABASE_URL: {db_url}')
except Exception as e:
    print(f'   Error: {e}')
"

# 3. Parse DATABASE_URL components
echo ""
echo "3. Parsed DATABASE_URL Components:"
python3 -c "
from urllib.parse import urlparse
import os
db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    parsed = urlparse(db_url)
    print(f'   Scheme: {parsed.scheme}')
    print(f'   Username: {parsed.username}')
    print(f'   Password: {\"*\" * len(parsed.password) if parsed.password else \"(empty)\"}')
    print(f'   Hostname: {parsed.hostname}')
    print(f'   Port: {parsed.port}')
    print(f'   Database: {parsed.path.lstrip(\"/\")}')
else:
    print('   DATABASE_URL not set')
"

# 4. Test MySQL hostname resolution
echo ""
echo "4. MySQL Hostname Resolution:"
python3 -c "
import socket
hosts = ['mysql', 'localhost', '127.0.0.1']
for host in hosts:
    try:
        ip = socket.gethostbyname(host)
        print(f'   {host} -> {ip} ✓')
    except socket.gaierror as e:
        print(f'   {host} -> ERROR: {e}')
"

# 5. Test MySQL port connectivity
echo ""
echo "5. MySQL Port Connectivity:"
python3 -c "
import socket
hosts = ['mysql', 'localhost']
port = 3306
for host in hosts:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            print(f'   {host}:{port} -> Reachable ✓')
        else:
            print(f'   {host}:{port} -> Not reachable ✗')
    except Exception as e:
        print(f'   {host}:{port} -> ERROR: {e}')
"

echo ""
echo "=== Check Complete ==="











