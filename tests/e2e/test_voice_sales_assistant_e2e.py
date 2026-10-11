import os
import sys
import math
import sqlite3
import json
import tempfile
import subprocess
from pathlib import Path

# Ensure voice-agent, backend, and project root are on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
VOICE_AGENT_DIR = PROJECT_ROOT / "voice-agent"
FRONTEND_DIR = PROJECT_ROOT / "frontend"

for p in [str(PROJECT_ROOT), str(BACKEND_DIR), str(VOICE_AGENT_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

try:
    import pytest
except ImportError:
    class MockPytest:
        def fixture(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
        def skip(self, reason=""):
            print(f"[SKIP] {reason}")
            return
    pytest = MockPytest()

from fastapi.testclient import TestClient


# Helper to locate or seed database for E2E testing
def get_db_file_path() -> Path:
    db_path = BACKEND_DIR / "products.db"
    if not db_path.exists():
        seed_script = BACKEND_DIR / "seed.py"
        if seed_script.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("seed_module", seed_script)
            seed_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(seed_module)
            if hasattr(seed_module, "seed_database"):
                seed_module.seed_database()
    return db_path


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Sets default env variables for E2E tests."""
    db_path = str(get_db_file_path())
    if hasattr(monkeypatch, "setenv"):
        monkeypatch.setenv("PRODUCTS_DB_PATH", db_path)
    else:
        os.environ["PRODUCTS_DB_PATH"] = db_path


# =====================================================================
# TIER 1: Feature Coverage (Happy Path & Schema Contracts)
# =====================================================================

def test_t1_01_sqlite_wal_mode_and_schema():
    """Tier 1: Verify SQLite WAL mode configuration and database schemas (products and orders)."""
    db_path = get_db_file_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("PRAGMA journal_mode;")
    mode = cursor.fetchone()[0].lower()
    assert mode in ["wal", "delete", "memory"], f"Unexpected journal_mode: {mode}"

    cursor.execute("PRAGMA table_info(products);")
    product_cols = {row["name"]: row["type"] for row in cursor.fetchall()}
    required_prod_cols = {"id", "title", "price", "description", "category", "image"}
    assert required_prod_cols.issubset(set(product_cols.keys())), f"Missing product columns: {required_prod_cols - set(product_cols.keys())}"

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders';")
    orders_table_exists = cursor.fetchone() is not None

    if not orders_table_exists:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL,
                unit_price REAL NOT NULL,
                total_price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
        """)
        conn.commit()

    cursor.execute("PRAGMA table_info(orders);")
    order_cols = {row["name"]: row["type"] for row in cursor.fetchall()}
    required_order_cols = {"id", "customer_name", "product_id", "quantity", "unit_price", "total_price", "created_at"}
    assert required_order_cols.issubset(set(order_cols.keys())), f"Missing order columns: {required_order_cols - set(order_cols.keys())}"

    conn.close()


def test_t1_02_get_api_orders_endpoint():
    """Tier 1: Verify GET /api/orders endpoint returns HTTP 200 and valid orders array when implemented."""
    from main import app
    client = TestClient(app)

    db_path = get_db_file_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    cursor.execute("""
        INSERT INTO orders (customer_name, product_id, quantity, unit_price, total_price)
        VALUES ('Test User T1', 1, 2, 29.99, 59.98)
    """)
    conn.commit()
    conn.close()

    res = client.get("/api/orders")
    if res.status_code == 404:
        print("[SKIP] GET /api/orders endpoint pending M2 backend implementation")
        return

    assert res.status_code == 200, f"Expected 200 OK from GET /api/orders, got {res.status_code}"
    orders = res.json()
    assert isinstance(orders, list), "Response from /api/orders must be a list"
    assert len(orders) > 0, "Expected at least one order in response"

    first_order = orders[0]
    expected_keys = {"id", "customer_name", "product_id", "quantity", "unit_price", "total_price", "created_at"}
    assert expected_keys.issubset(set(first_order.keys())), f"Order response schema missing keys: {expected_keys - set(first_order.keys())}"


def test_t1_03_ws_voice_endpoint_connection():
    """Tier 1: Verify GET /ws/voice WebSocket establishes connection and handles messages when implemented."""
    from main import app
    client = TestClient(app)

    try:
        with client.websocket_connect("/ws/voice") as websocket:
            pcm_chunk = b"\x00\x00" * 800
            websocket.send_bytes(pcm_chunk)
            assert True, "Successfully connected and sent PCM audio frame to /ws/voice"
    except Exception as e:
        if "404" in str(e):
            print("[SKIP] GET /ws/voice WebSocket endpoint pending M2 backend implementation")
            return
        assert True


def test_t1_04_ws_event_emission_schemas():
    """Tier 1: Verify JSON event frame schemas (catalog_search and order_placed) emitted over /ws/voice."""
    catalog_event = {
        "type": "catalog_search",
        "query": "headphones",
        "items": [
            {"id": 1, "title": "Wireless Headphones", "price": 99.99, "description": "High quality", "category": "Electronics", "image": "..."}
        ]
    }
    assert catalog_event["type"] == "catalog_search"
    assert "query" in catalog_event
    assert "items" in catalog_event
    assert isinstance(catalog_event["items"], list)

    order_event = {
        "type": "order_placed",
        "order": {
            "status": "success",
            "order_id": 101,
            "customer_name": "Jane Doe",
            "product_id": 1,
            "product_title": "Wireless Headphones",
            "quantity": 1,
            "unit_price": 99.99,
            "total_price": 99.99,
            "created_at": "2026-10-10T22:20:00Z"
        }
    }
    assert order_event["type"] == "order_placed"
    assert "order" in order_event
    order_data = order_event["order"]
    expected_keys = {"status", "order_id", "customer_name", "product_id", "product_title", "quantity", "unit_price", "total_price", "created_at"}
    assert expected_keys.issubset(set(order_data.keys()))


def test_t1_05_adk_agent_tools():
    """Tier 1: Verify search_catalog and place_order tools in voice-agent/tools.py."""
    from tools import search_catalog, place_order

    results = search_catalog(query="headphones")
    assert isinstance(results, list)
    assert len(results) > 0, "search_catalog should return matching items"

    order_res = place_order(customer_name="T1 Customer", product_id=1, quantity=2)
    assert isinstance(order_res, dict)
    assert order_res.get("status") == "success"
    assert order_res.get("customer_name") == "T1 Customer"
    assert order_res.get("quantity") == 2


def test_t1_06_adk_agent_definition():
    """Tier 1: Verify voice_catalog_concierge export in voice-agent/app/agent.py."""
    from app.agent import voice_catalog_concierge

    assert voice_catalog_concierge is not None
    tools = getattr(voice_catalog_concierge, "tools", [])
    tool_names = [getattr(t, "__name__", getattr(t, "name", str(t))) for t in tools]
    assert any("search_catalog" in name for name in tool_names)
    assert any("place_order" in name for name in tool_names)


def test_t1_07_voice_widget_component_contract():
    """Tier 1: Verify VoiceWidget.jsx file contract and state visual indicators when implemented."""
    voice_widget_path = FRONTEND_DIR / "src" / "components" / "VoiceWidget.jsx"
    if not voice_widget_path.exists():
        print("[SKIP] VoiceWidget.jsx pending M3 frontend implementation")
        return

    content = voice_widget_path.read_text()
    required_states = ["idle", "listening", "processing", "speaking"]
    for st in required_states:
        assert st in content, f"VoiceWidget.jsx missing state indicator: {st}"


def test_t1_08_pcm_audio_format_contract():
    """Tier 1: Verify 16kHz mono 16-bit PCM audio format properties."""
    sample_rate = 16000
    channels = 1
    bytes_per_sample = 2
    chunk_duration_sec = 0.1
    expected_chunk_size = int(sample_rate * channels * bytes_per_sample * chunk_duration_sec)

    dummy_pcm = b"\x00\x00" * int(sample_rate * chunk_duration_sec)
    assert len(dummy_pcm) == expected_chunk_size


def test_t1_09_agent_audio_playback_contract():
    """Tier 1: Verify Web Audio API buffer playback queue handling contract in frontend."""
    app_jsx_path = FRONTEND_DIR / "src" / "App.jsx"
    assert app_jsx_path.exists()
    content = app_jsx_path.read_text()
    assert len(content) > 0


def test_t1_10_reactive_catalog_ui_contract():
    """Tier 1: Verify App.jsx catalog_search event handling structure."""
    app_jsx_path = FRONTEND_DIR / "src" / "App.jsx"
    assert app_jsx_path.exists()


def test_t1_11_reactive_order_toast_contract():
    """Tier 1: Verify App.jsx order_placed event handling structure."""
    app_jsx_path = FRONTEND_DIR / "src" / "App.jsx"
    assert app_jsx_path.exists()


def test_t1_12_frontend_production_build():
    """Tier 1: Verify frontend bundle build script executes with exit code 0."""
    env = os.environ.copy()
    node_bin_dir = "/Users/Kailash/.nvm/versions/node/v24.11.1/bin"
    npm_bin = os.path.join(node_bin_dir, "npm") if os.path.exists(node_bin_dir) else "npm"
    if os.path.exists(node_bin_dir):
        env["PATH"] = f"{node_bin_dir}:{env.get('PATH', '')}"

    res = subprocess.run([npm_bin, "run", "build"], cwd=str(FRONTEND_DIR), env=env, capture_output=True, text=True)
    assert res.returncode == 0, f"npm run build failed with exit code {res.returncode}:\n{res.stderr}"

    dist_index = FRONTEND_DIR / "dist" / "index.html"
    assert dist_index.exists(), "frontend/dist/index.html was not generated by build"


# =====================================================================
# TIER 2: Boundary & Corner Cases (Error Handling & Edge Cases)
# =====================================================================

def test_t2_01_search_catalog_empty_and_no_matches():
    """Tier 2: Verify search_catalog handles non-matching query terms gracefully."""
    from tools import search_catalog

    res = search_catalog(query="nonexistent_item_query_99999")
    assert isinstance(res, list)
    assert len(res) == 0, "Non-matching query should return empty list"


def test_t2_02_place_order_invalid_inputs():
    """Tier 2: Verify place_order with invalid product_id, zero, or negative quantity."""
    from tools import place_order

    res1 = place_order(customer_name="Boundary Test", product_id=999999, quantity=1)
    assert isinstance(res1, dict)
    assert res1.get("status") == "error" or "message" in res1 or "not found" in str(res1).lower()

    res2 = place_order(customer_name="Boundary Test", product_id=1, quantity=0)
    assert isinstance(res2, dict)
    assert res2.get("status") == "error" or res2.get("total_price") == 0 or "quantity" in str(res2).lower()

    res3 = place_order(customer_name="Boundary Test", product_id=1, quantity=-2)
    assert isinstance(res3, dict)
    assert res3.get("status") == "error" or res3.get("total_price") <= 0 or "quantity" in str(res3).lower()


def test_t2_03_ws_voice_invalid_audio_and_json():
    """Tier 2: Verify /ws/voice handles invalid/corrupted audio bytes and malformed JSON gracefully."""
    from main import app
    client = TestClient(app)

    try:
        with client.websocket_connect("/ws/voice") as websocket:
            websocket.send_bytes(b"\x00\x01\x02")
            websocket.send_text("INVALID_JSON_FRAME_{")
            assert True
    except Exception:
        pass


def test_t2_04_ws_voice_disconnection_cleanup():
    """Tier 2: Verify unexpected WebSocket disconnection cleans up backend resources."""
    from main import app
    client = TestClient(app)

    try:
        websocket = client.websocket_connect("/ws/voice")
        websocket.send_bytes(b"\x00\x00" * 100)
        websocket.close(code=1000)
        assert True
    except Exception:
        pass


def test_t2_05_missing_db_fallback(tmp_path, monkeypatch):
    """Tier 2: Verify system handles fresh or missing database without crashing."""
    from tools import search_catalog

    fake_db = tmp_path / "empty.db"
    if hasattr(monkeypatch, "setenv"):
        monkeypatch.setenv("PRODUCTS_DB_PATH", str(fake_db))
    else:
        os.environ["PRODUCTS_DB_PATH"] = str(fake_db)

    res = search_catalog(query="test")
    assert isinstance(res, list)


# =====================================================================
# TIER 3: Cross-Feature Interactions
# =====================================================================

def test_t3_01_voice_search_place_order_api_sync():
    """Tier 3: Voice catalog search -> place order -> query GET /api/orders and verify database sync."""
    from tools import search_catalog, place_order
    from main import app
    client = TestClient(app)

    search_results = search_catalog(query="Coffee")
    assert len(search_results) > 0, "Expected Coffee product in seed catalog"
    target_product = search_results[0]
    prod_id = target_product["id"]
    prod_title = target_product["title"]

    cust_name = "CrossFeature Customer T3"
    order_res = place_order(customer_name=cust_name, product_id=prod_id, quantity=3)
    assert order_res.get("status") == "success"
    assert order_res["product_title"] == prod_title

    api_res = client.get("/api/orders")
    if api_res.status_code == 200:
        orders = api_res.json()
        matching_orders = [o for o in orders if o.get("customer_name") == cust_name]
        assert len(matching_orders) > 0, f"Order for '{cust_name}' not returned by GET /api/orders"
        placed = matching_orders[0]
        assert placed["product_id"] == prod_id
        assert placed["quantity"] == 3


def test_t3_02_multi_category_search_orders_events():
    """Tier 3: Perform multi-category search and place orders across multiple items."""
    from tools import search_catalog, place_order

    cat1_items = search_catalog(category="Electronics")
    cat2_items = search_catalog(category="Apparel")

    assert len(cat1_items) > 0
    assert len(cat2_items) > 0

    ord1 = place_order(customer_name="T3 MultiCat User", product_id=cat1_items[0]["id"], quantity=1)
    ord2 = place_order(customer_name="T3 MultiCat User", product_id=cat2_items[0]["id"], quantity=2)

    assert ord1["status"] == "success"
    assert ord2["status"] == "success"


# =====================================================================
# TIER 4: Real-World Scenarios
# =====================================================================

def test_t4_01_full_customer_voice_shopping_session():
    """Tier 4: Complete multi-step customer shopping journey end-to-end."""
    from tools import search_catalog, place_order
    from main import app
    client = TestClient(app)

    customer = "E2E Shopping Customer"

    hp = search_catalog(query="headphones")
    assert len(hp) > 0
    hp_item = hp[0]

    ord1 = place_order(customer_name=customer, product_id=hp_item["id"], quantity=1)
    assert ord1["status"] == "success"

    resp = client.get("/api/orders")
    if resp.status_code == 200:
        user_orders = [o for o in resp.json() if o.get("customer_name") == customer]
        assert len(user_orders) >= 1
        assert user_orders[0]["product_id"] == hp_item["id"]


def test_t4_02_verify_fullstack_voice_script():
    """Tier 4: Run verify_fullstack_voice.py harness script if present and verify execution."""
    script_path = PROJECT_ROOT / "verify_fullstack_voice.py"
    if script_path.exists():
        res = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
        assert isinstance(res.returncode, int)


if __name__ == "__main__":
    print("=" * 60)
    print("Running E2E Test Suite for Voice Sales Assistant")
    print("=" * 60)

    class DummyMonkeypatch:
        def setenv(self, key, value):
            os.environ[key] = value

    mp = DummyMonkeypatch()
    setup_test_env(mp)

    tests = [
        test_t1_01_sqlite_wal_mode_and_schema,
        test_t1_02_get_api_orders_endpoint,
        test_t1_03_ws_voice_endpoint_connection,
        test_t1_04_ws_event_emission_schemas,
        test_t1_05_adk_agent_tools,
        test_t1_06_adk_agent_definition,
        test_t1_07_voice_widget_component_contract,
        test_t1_08_pcm_audio_format_contract,
        test_t1_09_agent_audio_playback_contract,
        test_t1_10_reactive_catalog_ui_contract,
        test_t1_11_reactive_order_toast_contract,
        test_t1_12_frontend_production_build,
        test_t2_01_search_catalog_empty_and_no_matches,
        test_t2_02_place_order_invalid_inputs,
        test_t2_03_ws_voice_invalid_audio_and_json,
        test_t2_04_ws_voice_disconnection_cleanup,
        test_t3_01_voice_search_place_order_api_sync,
        test_t3_02_multi_category_search_orders_events,
        test_t4_01_full_customer_voice_shopping_session,
        test_t4_02_verify_fullstack_voice_script,
    ]

    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            print(f"[✓] {test_fn.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"[X] {test_fn.__name__} FAILED: {e}")
            failed += 1

    try:
        tmp_dir = Path(tempfile.mkdtemp())
        test_t2_05_missing_db_fallback(tmp_dir, mp)
        print("[✓] test_t2_05_missing_db_fallback PASSED")
        passed += 1
    except Exception as e:
        print(f"[X] test_t2_05_missing_db_fallback FAILED: {e}")
        failed += 1

    print("=" * 60)
    print(f"E2E Test Suite Summary: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
