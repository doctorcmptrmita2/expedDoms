"""
Test uygulama başlatma
"""
import sys
import traceback

try:
    print("1. Import test...")
    from app.main import app
    print("✅ App import OK")
    
    print("\n2. Router test...")
    from app.api.v1 import import_api
    print("✅ Import API router OK")
    
    print("\n3. Endpoint test...")
    routes = [r for r in app.routes if hasattr(r, 'path') and 'single-zone' in r.path]
    print(f"✅ Found {len(routes)} single-zone routes")
    for r in routes:
        print(f"   - {r.path} ({r.methods})")
    
    print("\n✅ Tüm testler başarılı!")
    
except Exception as e:
    print(f"\n❌ HATA: {e}")
    traceback.print_exc()
    sys.exit(1)








