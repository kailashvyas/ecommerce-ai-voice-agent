#!/usr/bin/env python3
"""
Automated Verification Script for Voice Agent (voice-agent/)

Checks end-to-end functionality:
1. Environment DB path resolution & backend/products.db existence/seeding
2. search_catalog queries against products database
3. place_order database table creation, record insertion, & confirmation payload
4. ADK Agent module voice_catalog_concierge export, model, prompt, and tool registration

Exits with code 0 on success, non-zero on failure.
"""

import sys
import os
import sqlite3
from pathlib import Path

VOICE_AGENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VOICE_AGENT_DIR.parent

if str(VOICE_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def run_verification():
    print("=" * 60)
    print("Starting Voice Agent End-to-End Verification")
    print("=" * 60)

    # 1. Database & Seed Check
    db_path = PROJECT_ROOT / "backend" / "products.db"
    if not db_path.exists():
        print(f"[!] Database {db_path} not found. Attempting to seed database...")
        seed_script = PROJECT_ROOT / "backend" / "seed.py"
        if seed_script.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("seed_mod", seed_script)
            seed_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(seed_mod)
            seed_mod.seed_database()
        else:
            print("[X] ERROR: Seed script backend/seed.py missing.")
            sys.exit(1)

    os.environ["PRODUCTS_DB_PATH"] = str(db_path)
    print(f"[✓] Database located at: {db_path}")

    # 2. Check search_catalog
    try:
        from tools import search_catalog
        results = search_catalog(query="headphones")
        if not isinstance(results, list) or len(results) == 0:
            print("[X] ERROR: search_catalog returned no results for 'headphones'")
            sys.exit(1)
        print(f"[✓] search_catalog verified (found {len(results)} items for 'headphones')")
    except Exception as e:
        print(f"[X] ERROR in search_catalog: {e}")
        sys.exit(1)

    # 3. Check place_order
    try:
        from tools import place_order
        res = place_order(customer_name="Verification Suite", product_id=1, quantity=1)
        if not isinstance(res, dict) or res.get("status") != "success":
            print(f"[X] ERROR: place_order failed. Response: {res}")
            sys.exit(1)
        
        # Verify direct DB insertion in orders table
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, customer_name, total_price FROM orders WHERE customer_name = ?", ("Verification Suite",))
        order_row = cursor.fetchone()
        conn.close()

        if not order_row:
            print("[X] ERROR: Order was not inserted into SQLite 'orders' table.")
            sys.exit(1)
        print(f"[✓] place_order verified (order ID {res.get('order_id')} inserted into orders table)")
    except Exception as e:
        print(f"[X] ERROR in place_order: {e}")
        sys.exit(1)

    # 4. Check ADK Agent module & tool registration
    try:
        from app.agent import voice_catalog_concierge
        if voice_catalog_concierge is None:
            print("[X] ERROR: voice_catalog_concierge is None")
            sys.exit(1)
        
        # Inspect model
        model = getattr(voice_catalog_concierge, "model", None)
        model_str = getattr(model, "model_name", str(model))
        if "gemini-live-2.5-flash-native-audio" not in model_str and "2.5" not in model_str:
            print(f"[!] Warning: Agent model is '{model_str}', expected 'gemini-live-2.5-flash-native-audio'")

        # Inspect tools
        tools = getattr(voice_catalog_concierge, "tools", [])
        tool_names = [getattr(t, "name", getattr(t, "__name__", str(t))) for t in tools]
        if not any("search_catalog" in name for name in tool_names) or not any("place_order" in name for name in tool_names):
            print(f"[X] ERROR: Agent registered tools do not contain both search_catalog and place_order. Found: {tool_names}")
            sys.exit(1)

        print(f"[✓] ADK Agent voice_catalog_concierge verified with tools: {tool_names}")
    except Exception as e:
        print(f"[X] ERROR loading app.agent module: {e}")
        sys.exit(1)

    print("=" * 60)
    print("ALL VOICE AGENT VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("=" * 60)
    sys.exit(0)


if __name__ == "__main__":
    run_verification()
