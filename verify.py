#!/usr/bin/env python3
"""
Automated Verification Suite for E-Commerce Product Catalog Application.
Validates:
1. Database Seeding (python backend/seed.py populates 25 items in backend/products.db)
2. FastAPI GET /api/products?page=1&limit=6 (Status 200, 6 items, metadata, CORS header)
3. FastAPI GET /api/products?page=5&limit=6 (Status 200, 1 item, metadata)
4. Frontend Build (npm run build in frontend/ exits 0 with dist/ generated)
"""

import sys
import os
import sqlite3
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"

def log(msg, status="INFO"):
    symbol = "✓" if status == "PASS" else ("✗" if status == "FAIL" else "ℹ")
    print(f"[{symbol}] [{status}] {msg}", flush=True)

def test_database_seeding():
    print("\n--- Test 1: Database Seeding ---", flush=True)
    seed_script = BACKEND_DIR / "seed.py"
    if not seed_script.exists():
        log("backend/seed.py does not exist", "FAIL")
        return False

    res = subprocess.run([sys.executable, str(seed_script)], capture_output=True, text=True)
    if res.returncode != 0:
        log(f"seed.py failed: {res.stderr}", "FAIL")
        return False

    db_file = BACKEND_DIR / "products.db"
    if not db_file.exists():
        log("backend/products.db was not created", "FAIL")
        return False

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products;")
    count = cursor.fetchone()[0]
    conn.close()

    if count == 25:
        log(f"Database seeded successfully with exactly {count} distinct products.", "PASS")
        return True
    else:
        log(f"Expected 25 seeded items, but found {count}.", "FAIL")
        return False

def test_backend_api():
    print("\n--- Test 2 & 3: FastAPI Endpoint & CORS Checks ---", flush=True)
    sys.path.insert(0, str(BACKEND_DIR))
    
    try:
        from fastapi.testclient import TestClient
        from main import app
    except Exception as e:
        log(f"Failed to import FastAPI app from backend/main.py: {e}", "FAIL")
        return False

    client = TestClient(app)

    # Check 1: GET /api/products?page=1&limit=6
    res1 = client.get("/api/products?page=1&limit=6", headers={"Origin": "http://localhost:3000"})
    if res1.status_code != 200:
        log(f"GET /api/products?page=1&limit=6 returned HTTP {res1.status_code}", "FAIL")
        return False

    data1 = res1.json()
    items1 = data1.get("data", [])
    meta1 = data1.get("metadata", {})

    if len(items1) != 6:
        log(f"Page 1 expected 6 items, got {len(items1)}", "FAIL")
        return False

    expected_meta1 = {"page": 1, "limit": 6, "total_items": 25, "total_pages": 5}
    for k, v in expected_meta1.items():
        if meta1.get(k) != v:
            log(f"Page 1 metadata key '{k}' expected {v}, got {meta1.get(k)}", "FAIL")
            return False

    cors_header = res1.headers.get("access-control-allow-origin")
    if not cors_header:
        log("CORS header access-control-allow-origin is missing in response", "FAIL")
        return False

    log("GET /api/products?page=1&limit=6 returned 200 OK with 6 items, valid metadata & CORS header.", "PASS")

    # Check 2: GET /api/products?page=5&limit=6
    res2 = client.get("/api/products?page=5&limit=6")
    if res2.status_code != 200:
        log(f"GET /api/products?page=5&limit=6 returned HTTP {res2.status_code}", "FAIL")
        return False

    data2 = res2.json()
    items2 = data2.get("data", [])
    meta2 = data2.get("metadata", {})

    if len(items2) != 1:
        log(f"Page 5 expected 1 item, got {len(items2)}", "FAIL")
        return False

    expected_meta2 = {"page": 5, "limit": 6, "total_items": 25, "total_pages": 5}
    for k, v in expected_meta2.items():
        if meta2.get(k) != v:
            log(f"Page 5 metadata key '{k}' expected {v}, got {meta2.get(k)}", "FAIL")
            return False

    log("GET /api/products?page=5&limit=6 returned 200 OK with 1 final item & valid metadata.", "PASS")
    return True

def test_frontend_build():
    print("\n--- Test 4: Frontend Build Compilation ---", flush=True)
    if not FRONTEND_DIR.exists():
        log("frontend/ directory does not exist", "FAIL")
        return False

    env = os.environ.copy()
    node_bin_dir = "/Users/Kailash/.nvm/versions/node/v24.11.1/bin"
    npm_bin = os.path.join(node_bin_dir, "npm") if os.path.exists(node_bin_dir) else "npm"
    if os.path.exists(node_bin_dir):
        env["PATH"] = f"{node_bin_dir}:{env.get('PATH', '')}"

    res = subprocess.run([npm_bin, "run", "build"], cwd=str(FRONTEND_DIR), env=env, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"npm run build failed with exit code {res.returncode}:\n{res.stderr}", "FAIL")
        return False

    dist_index = FRONTEND_DIR / "dist" / "index.html"
    if not dist_index.exists():
        log("frontend/dist/index.html was not generated by build", "FAIL")
        return False

    log("Frontend build compiled cleanly with exit code 0 and generated dist/index.html.", "PASS")
    return True

def main():
    print("==================================================", flush=True)
    print("  E-COMMERCE PRODUCT CATALOG VERIFICATION SUITE   ", flush=True)
    print("==================================================", flush=True)

    results = [
        test_database_seeding(),
        test_backend_api(),
        test_frontend_build()
    ]

    print("\n==================================================", flush=True)
    if all(results):
        print("  ALL VERIFICATION CHECKS PASSED (100% SUCCESS)   ", flush=True)
        print("==================================================", flush=True)
        sys.exit(0)
    else:
        print("  VERIFICATION FAILED (SOME CHECKS DID NOT PASS)  ", flush=True)
        print("==================================================", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
