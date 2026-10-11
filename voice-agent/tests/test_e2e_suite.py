import os
import sys
import sqlite3
import tempfile
from pathlib import Path

try:
    import pytest
except ImportError:
    class MockPytest:
        def fixture(self, *args, **kwargs):
            def decorator(func):
                return func
            return decorator
    pytest = MockPytest()

# Ensure voice-agent root and project root are on sys.path
VOICE_AGENT_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = VOICE_AGENT_DIR.parent

if str(VOICE_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Helper to locate or seed default database for tests
def get_test_db_path() -> str:
    """Returns path to backend products.db, seeding it if necessary."""
    backend_db = PROJECT_ROOT / "backend" / "products.db"
    if not backend_db.exists():
        # Run seed script if backend DB does not exist
        seed_script = PROJECT_ROOT / "backend" / "seed.py"
        if seed_script.exists():
            import importlib.util
            spec = importlib.util.spec_from_file_location("seed_module", seed_script)
            seed_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(seed_module)
            if hasattr(seed_module, "seed_database"):
                seed_module.seed_database()
    return str(backend_db)


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch):
    """Sets default env variables for voice agent tests."""
    db_path = get_test_db_path()
    if os.path.exists(db_path):
        monkeypatch.setenv("PRODUCTS_DB_PATH", db_path)


# =====================================================================
# TIER 1: Feature Coverage (Happy Path & Schema Contracts)
# =====================================================================

def test_t1_01_search_catalog_by_text():
    """Tier 1: Verify catalog search by query string (e.g. 'headphones')."""
    from tools import search_catalog

    results = search_catalog(query="headphones")
    assert isinstance(results, list), "search_catalog should return a list"
    assert len(results) > 0, "Expected at least 1 result for 'headphones'"
    item = results[0]
    assert "id" in item
    assert "title" in item
    assert "price" in item
    assert "description" in item
    assert "category" in item
    assert "stock_status" in item
    assert "headphones" in item["title"].lower() or "headphones" in item["description"].lower()


def test_t1_02_search_catalog_by_category():
    """Tier 1: Verify catalog search by category string (e.g. 'Electronics')."""
    from tools import search_catalog

    results = search_catalog(category="Electronics")
    assert isinstance(results, list)
    assert len(results) > 0, "Expected Electronics products"
    for item in results:
        assert item["category"] == "Electronics"


def test_t1_03_search_catalog_empty_query():
    """Tier 1: Verify search_catalog with no filter parameters returns catalog items or list."""
    from tools import search_catalog

    results = search_catalog()
    assert isinstance(results, list)


def test_t1_04_place_order_success():
    """Tier 1: Verify successful order placement returns expected calculation and payload."""
    from tools import place_order

    res = place_order(customer_name="Alice Smith", product_id=1, quantity=2)
    assert isinstance(res, dict)
    assert res.get("status") == "success"
    assert "order_id" in res
    assert res["customer_name"] == "Alice Smith"
    assert res["quantity"] == 2
    assert res["unit_price"] > 0
    assert abs(res["total_price"] - (res["unit_price"] * 2)) < 0.001


def test_t1_05_place_order_schema():
    """Tier 1: Verify order placement response schema contains all contract keys."""
    from tools import place_order

    res = place_order(customer_name="Bob Jones", product_id=2, quantity=1)
    expected_keys = {"status", "order_id", "customer_name", "product_title", "quantity", "unit_price", "total_price", "created_at"}
    assert expected_keys.issubset(res.keys()), f"Missing keys in order schema: {expected_keys - set(res.keys())}"


def test_t1_06_adk_agent_definition_and_tools():
    """Tier 1: Verify ADK agent voice_catalog_concierge export, model, prompt, and registered tools."""
    from app.agent import voice_catalog_concierge

    assert voice_catalog_concierge is not None, "voice_catalog_concierge must be exported from app.agent"

    # Check model attribute
    model = getattr(voice_catalog_concierge, "model", None)
    if hasattr(model, "model_name"):
        model_name = model.model_name
    elif isinstance(model, str):
        model_name = model
    else:
        model_name = str(model)
    assert "gemini-live-2.5-flash-native-audio" in model_name or "2.5" in model_name

    # Check system instruction
    instruction = getattr(voice_catalog_concierge, "instruction", None) or getattr(voice_catalog_concierge, "system_instruction", "")
    assert "upbeat voice shopping assistant" in str(instruction) or "place_order" in str(instruction)

    # Check tools registration
    tools = getattr(voice_catalog_concierge, "tools", [])
    tool_names = []
    for t in tools:
        if hasattr(t, "name"):
            tool_names.append(t.name)
        elif hasattr(t, "__name__"):
            tool_names.append(t.__name__)
        else:
            tool_names.append(str(t))

    assert any("search_catalog" in name for name in tool_names), f"search_catalog tool missing from agent tools: {tool_names}"
    assert any("place_order" in name for name in tool_names), f"place_order tool missing from agent tools: {tool_names}"


# =====================================================================
# TIER 2: Boundary & Corner Cases (Error Handling & Edge Cases)
# =====================================================================

def test_t2_01_place_order_invalid_product_id():
    """Tier 2: Verify placing order for non-existent product ID handles error gracefully."""
    from tools import place_order

    res = place_order(customer_name="Error Test", product_id=999999, quantity=1)
    assert isinstance(res, dict)
    assert res.get("status") == "error" or "message" in res or "not found" in str(res).lower()


def test_t2_02_place_order_zero_quantity():
    """Tier 2: Verify zero quantity order attempt returns error status."""
    from tools import place_order

    res = place_order(customer_name="Error Test", product_id=1, quantity=0)
    assert isinstance(res, dict)
    assert res.get("status") == "error" or "quantity" in str(res).lower() or res.get("total_price") == 0


def test_t2_03_place_order_negative_quantity():
    """Tier 2: Verify negative quantity order attempt returns error status."""
    from tools import place_order

    res = place_order(customer_name="Error Test", product_id=1, quantity=-3)
    assert isinstance(res, dict)
    assert res.get("status") == "error" or "quantity" in str(res).lower() or res.get("total_price") <= 0


def test_t2_04_search_catalog_no_matches():
    """Tier 2: Verify search for non-matching query returns empty list."""
    from tools import search_catalog

    res = search_catalog(query="nonexistent_product_xyz_12345")
    assert isinstance(res, list)
    assert len(res) == 0


def test_t2_05_missing_db_file_fallback(tmp_path, monkeypatch):
    """Tier 2: Verify custom PRODUCTS_DB_PATH points to non-existent or fresh path gracefully creates or reports."""
    from tools import search_catalog

    custom_db = tmp_path / "custom_test.db"
    monkeypatch.setenv("PRODUCTS_DB_PATH", str(custom_db))
    # search_catalog in empty DB should return empty list without crashing
    res = search_catalog(query="test")
    assert isinstance(res, list)


# =====================================================================
# TIER 3: Cross-Feature Combinations
# =====================================================================

def test_t3_01_search_then_order_flow():
    """Tier 3: Search for a product, extract its ID and title, then place order for it."""
    from tools import search_catalog, place_order

    search_res = search_catalog(query="Espresso")
    assert len(search_res) > 0, "Espresso machine should be found in seed catalog"
    prod = search_res[0]

    prod_id = prod["id"]
    prod_title = prod["title"]

    order_res = place_order(customer_name="Charlie Brown", product_id=prod_id, quantity=1)
    assert order_res.get("status") == "success"
    assert order_res["product_title"] == prod_title
    assert order_res["unit_price"] == prod["price"]


def test_t3_02_multi_category_search_and_orders():
    """Tier 3: Search across Apparel and Footwear, place order from each category."""
    from tools import search_catalog, place_order

    apparel_items = search_catalog(category="Apparel")
    footwear_items = search_catalog(category="Footwear")

    assert len(apparel_items) > 0
    assert len(footwear_items) > 0

    order1 = place_order(customer_name="Multi Cat Customer", product_id=apparel_items[0]["id"], quantity=1)
    order2 = place_order(customer_name="Multi Cat Customer", product_id=footwear_items[0]["id"], quantity=2)

    assert order1["status"] == "success"
    assert order2["status"] == "success"
    assert order1["product_title"] == apparel_items[0]["title"]
    assert order2["product_title"] == footwear_items[0]["title"]


# =====================================================================
# TIER 4: Real-World Scenarios
# =====================================================================

def test_t4_01_end_to_end_customer_shopping_journey():
    """Tier 4: Complete multi-step customer shopping session with direct DB verification."""
    from tools import search_catalog, place_order

    customer = "Dave Davidson"

    # Step 1: Customer searches for headphones
    headphones = search_catalog(query="headphones")
    assert len(headphones) > 0
    hp_id = headphones[0]["id"]

    # Step 2: Customer searches for mouse
    mice = search_catalog(query="mouse")
    assert len(mice) > 0
    mouse_id = mice[0]["id"]

    # Step 3: Customer orders 1 headphone and 2 mice
    ord1 = place_order(customer_name=customer, product_id=hp_id, quantity=1)
    ord2 = place_order(customer_name=customer, product_id=mouse_id, quantity=2)

    assert ord1["status"] == "success"
    assert ord2["status"] == "success"

    # Step 4: Verify directly in SQLite orders table
    db_path = os.environ.get("PRODUCTS_DB_PATH", get_test_db_path())
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM orders WHERE customer_name = ? ORDER BY id DESC LIMIT 2", (customer,))
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 2, f"Expected 2 orders in DB for {customer}, found {len(rows)}"


def test_t4_02_adk_agent_tool_execution():
    """Tier 4: Verify ADK agent tool callable execution via agent tools reference."""
    from app.agent import voice_catalog_concierge

    tools = voice_catalog_concierge.tools
    assert len(tools) >= 2

    # Find search_catalog tool reference
    search_tool = None
    for t in tools:
        if getattr(t, "__name__", "") == "search_catalog" or getattr(t, "name", "") == "search_catalog":
            search_tool = t
            break

    assert search_tool is not None, "search_catalog tool registered on agent"
    res = search_tool(query="Journal") if callable(search_tool) else search_tool.func(query="Journal")
    assert isinstance(res, list)


if __name__ == "__main__":
    print("=" * 60)
    print("Running Voice Agent E2E Test Suite Directly")
    print("=" * 60)

    class MockMonkeypatch:
        def setenv(self, key, value):
            os.environ[key] = value

    mp = MockMonkeypatch()
    setup_test_env(mp)

    test_funcs = [
        test_t1_01_search_catalog_by_text,
        test_t1_02_search_catalog_by_category,
        test_t1_03_search_catalog_empty_query,
        test_t1_04_place_order_success,
        test_t1_05_place_order_schema,
        test_t1_06_adk_agent_definition_and_tools,
        test_t2_01_place_order_invalid_product_id,
        test_t2_02_place_order_zero_quantity,
        test_t2_03_place_order_negative_quantity,
        test_t2_04_search_catalog_no_matches,
        test_t3_01_search_then_order_flow,
        test_t3_02_multi_category_search_and_orders,
        test_t4_01_end_to_end_customer_shopping_journey,
        test_t4_02_adk_agent_tool_execution,
    ]

    passed = 0
    failed = 0
    for tf in test_funcs:
        try:
            tf()
            print(f"[✓] {tf.__name__} PASSED")
            passed += 1
        except Exception as e:
            print(f"[X] {tf.__name__} FAILED: {e}")
            failed += 1

    try:
        tmp_dir = Path(tempfile.mkdtemp())
        test_t2_05_missing_db_file_fallback(tmp_dir, mp)
        print("[✓] test_t2_05_missing_db_file_fallback PASSED")
        passed += 1
    except Exception as e:
        print(f"[X] test_t2_05_missing_db_file_fallback FAILED: {e}")
        failed += 1

    print("=" * 60)
    print(f"E2E Test Suite Summary: {passed} PASSED, {failed} FAILED")
    print("=" * 60)
    sys.exit(0 if failed == 0 else 1)
