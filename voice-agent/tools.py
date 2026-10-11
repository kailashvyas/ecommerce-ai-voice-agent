import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    _curr_dir = Path(__file__).resolve().parent
    for _ef in [_curr_dir / ".env", _curr_dir.parent / ".env"]:
        if _ef.exists():
            load_dotenv(_ef)
except ImportError:
    pass


def get_db_path() -> Path:
    """Check PRODUCTS_DB_PATH env var, fallback to Path(__file__).resolve().parent.parent / "backend" / "products.db"."""
    env_path = os.environ.get("PRODUCTS_DB_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_absolute() and p.exists():
            return p
        va_rel = (Path(__file__).resolve().parent / env_path).resolve()
        if va_rel.exists():
            return va_rel
        root_rel = (Path(__file__).resolve().parent.parent / env_path).resolve()
        if root_rel.exists():
            return root_rel
        cwd_rel = Path(env_path).resolve()
        if cwd_rel.exists():
            return cwd_rel
    return (Path(__file__).resolve().parent.parent / "backend" / "products.db").resolve()


def get_db_connection() -> sqlite3.Connection:
    """Creates SQLite database connection with sqlite3.Row row factory."""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _escape_like(text: str) -> str:
    """Escapes special wildcard characters for SQLite LIKE queries."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_catalog(query: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
    """Filter products in backend/products.db using parameterized SQL LIKE ? ESCAPE '\\'.
    
    Returns dictionary list containing id, title, price, description, category, stock_status ('In Stock').
    Returns [] on error.
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = "SELECT id, title, price, description, category FROM products"
        where_clauses = []
        params = []

        if query and str(query).strip():
            escaped_q = f"%{_escape_like(str(query).strip())}%"
            where_clauses.append(
                "(title LIKE ? ESCAPE '\\' OR description LIKE ? ESCAPE '\\' OR category LIKE ? ESCAPE '\\')"
            )
            params.extend([escaped_q, escaped_q, escaped_q])

        if category and str(category).strip():
            escaped_c = f"%{_escape_like(str(category).strip())}%"
            where_clauses.append("category LIKE ? ESCAPE '\\'")
            params.append(escaped_c)

        if where_clauses:
            sql += " WHERE " + " AND ".join(where_clauses)

        sql += " ORDER BY id ASC"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append({
                "id": int(r["id"]),
                "title": str(r["title"]),
                "price": float(r["price"]),
                "description": str(r["description"]),
                "category": str(r["category"]),
                "stock_status": "In Stock"
            })
        return results
    except Exception:
        return []


def _ensure_orders_table(cursor: sqlite3.Cursor) -> None:
    """Ensures the orders table exists."""
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
        )
    """)


def place_order(customer_name: str, product_id: int, quantity: int) -> Dict[str, Any]:
    """Auto-create orders table if missing. Check product_id in products table.
    
    Calculate total_price = round(unit_price * quantity, 2).
    Insert row into orders table and commit.
    Return {"status": "success", "order_id": order_id, "customer_name": customer_name,
            "product_title": product_title, "quantity": quantity, "unit_price": unit_price,
            "total_price": total_price, "created_at": created_at}
    or {"status": "error", "message": ...}.
    """
    if not customer_name or not str(customer_name).strip():
        return {"status": "error", "message": "Customer name is required."}

    try:
        product_id = int(product_id)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return {"status": "error", "message": "Invalid product_id or quantity format."}

    if quantity <= 0:
        return {"status": "error", "message": "Quantity must be greater than zero."}

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        _ensure_orders_table(cursor)

        cursor.execute("SELECT id, title, price FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()

        if product is None:
            conn.close()
            return {"status": "error", "message": f"Product {product_id} not found."}

        unit_price = float(product["price"])
        product_title = str(product["title"])
        total_price = round(unit_price * quantity, 2)
        created_at = datetime.now(timezone.utc).isoformat()

        cursor.execute("""
            INSERT INTO orders (customer_name, product_id, quantity, unit_price, total_price, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(customer_name).strip(), product_id, quantity, unit_price, total_price, created_at))

        order_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return {
            "status": "success",
            "order_id": order_id,
            "customer_name": str(customer_name).strip(),
            "product_title": product_title,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
            "created_at": created_at
        }
    except Exception as e:
        return {"status": "error", "message": f"Database error: {str(e)}"}
