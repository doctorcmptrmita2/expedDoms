"""
Test script for debug page
"""
import urllib.request
import json

try:
    # Test debug page
    print("Testing /debug endpoint...")
    req = urllib.request.Request('http://localhost:8047/debug')
    req.add_header('User-Agent', 'Mozilla/5.0')
    
    with urllib.request.urlopen(req, timeout=10) as response:
        status = response.status
        content = response.read().decode('utf-8', errors='ignore')
        
        print(f"✅ Status: {status}")
        print(f"✅ Content length: {len(content)} bytes")
        print(f"✅ Has HTML: {'<!DOCTYPE' in content or '<html' in content}")
        print(f"✅ Has Debug title: {'Debug' in content}")
        print(f"✅ Has Tailwind: {'tailwindcss' in content.lower()}")
        
        # Check for common errors
        if 'error' in content.lower() and 'exception' in content.lower():
            print("⚠️  Possible error in content")
        else:
            print("✅ No obvious errors found")
            
        # Show first 200 chars
        print("\n📄 First 200 characters:")
        print(content[:200])
        
except urllib.error.URLError as e:
    print(f"❌ Connection error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()










