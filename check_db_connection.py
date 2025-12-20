#!/usr/bin/env python3
"""
Database connection test script.
Shows current DATABASE_URL and tests connection.
"""
import os
from urllib.parse import urlparse

print("=" * 60)
print("Database Connection Test")
print("=" * 60)

# Get DATABASE_URL from environment
db_url = os.environ.get('DATABASE_URL', 'NOT SET')
print(f"\nDATABASE_URL: {db_url[:80]}..." if len(db_url) > 80 else f"\nDATABASE_URL: {db_url}")

if db_url != 'NOT SET':
    try:
        parsed = urlparse(db_url)
        print(f"\nParsed Components:")
        print(f"  Scheme: {parsed.scheme}")
        print(f"  Username: {parsed.username}")
        print(f"  Password: {'*' * len(parsed.password) if parsed.password else '(empty)'}")
        print(f"  Hostname: {parsed.hostname}")
        print(f"  Port: {parsed.port}")
        print(f"  Database: {parsed.path.lstrip('/')}")
        
        # Test connection
        print(f"\nTesting connection to: {parsed.hostname}:{parsed.port}")
        print("Attempting to connect...")
        
        from app.core.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✓ Connection successful!")
            print(f"  Result: {result.fetchone()}")
            
    except Exception as e:
        print(f"\n✗ Connection failed!")
        print(f"  Error: {type(e).__name__}: {e}")
        print(f"\nPossible issues:")
        print(f"  1. MySQL service name might be wrong (current: {parsed.hostname})")
        print(f"     Expected: expireddomain_expireddomain-mysql")
        if parsed.hostname == 'mysql':
            print(f"     ⚠️  You're using 'mysql' but should use 'expireddomain_expireddomain-mysql'")
        print(f"  2. MySQL service might not be running")
        print(f"  3. Services might not be on the same network")
        print(f"  4. Password might be incorrect")
        print(f"\nTo fix:")
        print(f"  1. Go to EasyPanel → Your Project → Environment Variables")
        print(f"  2. Update DATABASE_URL to:")
        print(f"     mysql+pymysql://test:Tk990303005%40@expireddomain_expireddomain-mysql:3306/expireddomain")
        print(f"  3. Restart the container")
else:
    print("\n✗ DATABASE_URL not set in environment variables!")

print("\n" + "=" * 60)
print("To fix:")
print("1. Check MySQL service name in EasyPanel")
print("2. Update DATABASE_URL environment variable")
print("3. Format: mysql+pymysql://user:password@SERVICE_NAME:3306/database")
print("=" * 60)

