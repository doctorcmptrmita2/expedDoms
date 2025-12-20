#!/bin/bash
# Check DATABASE_URL environment variable

echo "=========================================="
echo "DATABASE_URL Environment Variable Check"
echo "=========================================="
echo ""

# Check if DATABASE_URL is set
if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL is NOT SET!"
else
    echo "✅ DATABASE_URL is set"
    echo ""
    echo "Current value:"
    echo "$DATABASE_URL" | sed 's/:[^:]*@/:****@/g'  # Hide password
    echo ""
    
    # Parse and show components
    echo "Parsed components:"
    python3 << EOF
from urllib.parse import urlparse
import os

db_url = os.environ.get('DATABASE_URL', '')
if db_url:
    parsed = urlparse(db_url)
    print(f"  Scheme: {parsed.scheme}")
    print(f"  Username: {parsed.username}")
    print(f"  Password: {'*' * len(parsed.password) if parsed.password else '(empty)'}")
    print(f"  Hostname: {parsed.hostname}")
    print(f"  Port: {parsed.port}")
    print(f"  Database: {parsed.path.lstrip('/')}")
    print("")
    print("⚠️  Expected hostname: expireddomain_expireddomain-mysql")
    print(f"   Current hostname: {parsed.hostname}")
    if parsed.hostname != 'expireddomain_expireddomain-mysql':
        print("   ❌ Hostname mismatch! Update DATABASE_URL in EasyPanel.")
    else:
        print("   ✅ Hostname is correct!")
else:
    print("  DATABASE_URL not found in environment")
EOF
fi

echo ""
echo "=========================================="









