import sys
sys.path.append('src')
from api.routes import router

print("Checking registered routes...")
for route in router.routes:
    if hasattr(route, 'path'):
        methods = list(route.methods) if hasattr(route, 'methods') and route.methods else ['GET']
        print(f"  {methods[0]} {route.path}")

print("\nLooking for /search endpoint...")
search_found = any(route.path == "/search" for route in router.routes if hasattr(route, 'path'))
print(f"Search endpoint found: {search_found}")
