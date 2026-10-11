import asyncio
import json
import math
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional, Any, Dict, List

# Ensure backend directory is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure voice-agent directory is in sys.path
VOICE_AGENT_DIR = Path(__file__).resolve().parent.parent / "voice-agent"
if str(VOICE_AGENT_DIR) not in sys.path:
    sys.path.insert(0, str(VOICE_AGENT_DIR))

try:
    from dotenv import load_dotenv
    for _env_path in [
        VOICE_AGENT_DIR / ".env",
        Path(__file__).resolve().parent.parent / ".env",
        Path(__file__).resolve().parent / ".env",
    ]:
        if _env_path.exists():
            load_dotenv(_env_path)
except ImportError:
    pass

try:
    import certifi
    if "SSL_CERT_FILE" not in os.environ:
        os.environ["SSL_CERT_FILE"] = certifi.where()
except ImportError:
    pass

from fastapi import FastAPI, Query, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict, RootModel

from database import get_db, DB_PATH, get_db_connection

# Attempt to import voice agent, tools, and ADK Live streaming components
try:
    from app.agent import voice_catalog_concierge
    from tools import search_catalog, place_order
except ImportError:
    try:
        from voice_agent.app.agent import voice_catalog_concierge
        from voice_agent.tools import search_catalog, place_order
    except ImportError:
        voice_catalog_concierge = None
        search_catalog = None
        place_order = None

try:
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.agents.live_request_queue import LiveRequestQueue, LiveRequest
    from google.genai import types
except ImportError:
    Runner = None
    InMemorySessionService = None
    LiveRequestQueue = None
    types = None


# --- Pydantic Schemas ---
class Product(BaseModel):
    id: int
    title: str
    price: float
    description: str
    category: str
    image: str

    model_config = ConfigDict(from_attributes=True)


class PaginationMetadata(BaseModel):
    page: int = Field(..., description="Current page number", ge=1)
    limit: int = Field(..., description="Items per page", ge=1)
    total_items: int = Field(..., description="Total items in dataset", ge=0)
    total_pages: int = Field(..., description="Total available pages", ge=0)


class PaginatedProductsResponse(BaseModel):
    data: list[Product]
    metadata: PaginationMetadata


class Order(BaseModel):
    id: int
    customer_name: str
    product_id: int
    quantity: int
    unit_price: float
    total_price: float
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class OrdersResponse(RootModel[list[Order]]):
    pass


# --- FastAPI App ---
app = FastAPI(
    title="E-Commerce Product Catalog API",
    description="API for browsing e-commerce product catalog with pagination",
    version="1.0.0",
)

# --- CORS Middleware ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/products", response_model=PaginatedProductsResponse)
def get_products(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(default=6, ge=1, le=100, description="Items per page"),
    db: sqlite3.Connection = Depends(get_db),
):
    try:
        cursor = db.cursor()

        # Count total items
        cursor.execute("SELECT COUNT(*) FROM products")
        row = cursor.fetchone()
        total_items = row[0] if row else 0

        # Calculate total pages
        total_pages = math.ceil(total_items / limit) if total_items > 0 else 0

        # Calculate offset and fetch products
        offset = (page - 1) * limit
        cursor.execute(
            "SELECT id, title, price, description, category, image FROM products ORDER BY id ASC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()

        products = [Product(**dict(r)) for r in rows] if rows else []

        return PaginatedProductsResponse(
            data=products,
            metadata=PaginationMetadata(
                page=page,
                limit=limit,
                total_items=total_items,
                total_pages=total_pages,
            ),
        )
    except sqlite3.OperationalError:
        # Fallback if database table does not exist yet
        return PaginatedProductsResponse(
            data=[],
            metadata=PaginationMetadata(
                page=page,
                limit=limit,
                total_items=0,
                total_pages=0,
            ),
        )


@app.get("/api/orders", response_model=OrdersResponse, status_code=200)
def get_orders(db: sqlite3.Connection = Depends(get_db)):
    """Fetch list of all placed orders from SQLite orders table."""
    try:
        cursor = db.cursor()
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
        db.commit()

        cursor.execute(
            "SELECT id, customer_name, product_id, quantity, unit_price, total_price, created_at FROM orders ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        orders = [Order(**dict(r)) for r in rows] if rows else []
        return OrdersResponse(orders)
    except sqlite3.OperationalError:
        return OrdersResponse([])


@app.websocket("/ws/voice")
async def websocket_voice(websocket: WebSocket):
    """WebSocket voice bridge routing audio to Google ADK Live Audio Agent."""
    await websocket.accept()

    event_queue: asyncio.Queue = asyncio.Queue()

    def session_search_catalog(query: Optional[str] = None, category: Optional[str] = None) -> List[Dict[str, Any]]:
        items = search_catalog(query=query, category=category) if search_catalog else []
        event = {
            "type": "catalog_search",
            "query": query or "",
            "items": items
        }
        event_queue.put_nowait(event)
        return items

    def session_place_order(customer_name: str, product_id: int, quantity: int) -> Dict[str, Any]:
        res = place_order(customer_name=customer_name, product_id=product_id, quantity=quantity) if place_order else {}
        if isinstance(res, dict) and res.get("status") == "success":
            event = {
                "type": "order_placed",
                "order": res
            }
            event_queue.put_nowait(event)
        return res

    async def broadcast_worker():
        try:
            while True:
                event = await event_queue.get()
                await websocket.send_json(event)
                event_queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

    broadcaster_task = asyncio.create_task(broadcast_worker())

    # Connect to Google ADK Live Session if agent and runner are available
    if voice_catalog_concierge is not None and Runner is not None:
        try:
            session_service = InMemorySessionService()
            runner = Runner(
                app_name="voice_catalog_concierge",
                agent=voice_catalog_concierge,
                session_service=session_service
            )
            session = await session_service.create_session(
                app_name="voice_catalog_concierge",
                user_id="web_shopper"
            )
            live_request_queue = LiveRequestQueue()

            async def forward_agent_events():
                try:
                    agen = runner.run_live(session=session, live_request_queue=live_request_queue)
                    async for event in agen:
                        # 1. Forward model generated voice audio bytes & transcript text
                        if event.content and event.content.parts:
                            for part in event.content.parts:
                                if part.inline_data and part.inline_data.data:
                                    # Send assistant voice audio bytes to client
                                    await websocket.send_bytes(part.inline_data.data)
                                if part.text:
                                    await websocket.send_json({
                                        "type": "transcript",
                                        "text": part.text
                                    })

                        # 2. Forward tool function responses to the frontend
                        for resp in event.get_function_responses():
                            if resp.name == "search_catalog":
                                res_val = resp.response
                                items = res_val.get("result", []) if isinstance(res_val, dict) else (res_val if isinstance(res_val, list) else [])
                                await websocket.send_json({
                                    "type": "catalog_search",
                                    "query": "",
                                    "items": items
                                })
                            elif resp.name == "place_order":
                                res_val = resp.response
                                order_dict = res_val.get("result", res_val) if isinstance(res_val, dict) else {}
                                await websocket.send_json({
                                    "type": "order_placed",
                                    "order": order_dict
                                })
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    print(f"Error in forward_agent_events: {e}", file=sys.stderr)

            forward_task = asyncio.create_task(forward_agent_events())

            try:
                while True:
                    message = await websocket.receive()
                    if "bytes" in message and message["bytes"]:
                        pcm_data = message["bytes"]
                        # Pipe client audio into Google ADK live streaming queue
                        live_request_queue.send_realtime(
                            types.Blob(data=pcm_data, mime_type="audio/pcm;rate=16000")
                        )
                    elif "text" in message and message["text"]:
                        raw_text = message["text"]
                        try:
                            data = json.loads(raw_text)
                            if "text" in data and data["text"]:
                                live_request_queue.send_content(
                                    types.Content(parts=[types.Part.from_text(text=data["text"])])
                                )
                            elif data.get("type") in ("search", "catalog_search", "search_catalog"):
                                session_search_catalog(query=data.get("query"), category=data.get("category"))
                            elif data.get("type") in ("order", "order_placed", "place_order"):
                                session_place_order(
                                    customer_name=data.get("customer_name") or "Customer",
                                    product_id=int(data.get("product_id", 1)),
                                    quantity=int(data.get("quantity", 1))
                                )
                        except (json.JSONDecodeError, TypeError, ValueError):
                            pass
            except (WebSocketDisconnect, RuntimeError):
                pass
            finally:
                live_request_queue.close()
                forward_task.cancel()
                try:
                    await forward_task
                except asyncio.CancelledError:
                    pass

        except (WebSocketDisconnect, RuntimeError):
            pass
        except Exception as err:
            print(f"ADK Live session init error: {err}", file=sys.stderr)
            # Fallback receive loop if ADK fails to connect
            try:
                while True:
                    message = await websocket.receive()
                    if "text" in message and message["text"]:
                        try:
                            data = json.loads(message["text"])
                            if data.get("type") in ("search", "catalog_search", "search_catalog"):
                                session_search_catalog(query=data.get("query"), category=data.get("category"))
                            elif data.get("type") in ("order", "order_placed", "place_order"):
                                session_place_order(
                                    customer_name=data.get("customer_name") or "Customer",
                                    product_id=int(data.get("product_id", 1)),
                                    quantity=int(data.get("quantity", 1))
                                )
                        except Exception:
                            pass
            except (WebSocketDisconnect, RuntimeError):
                pass

    else:
        # Fallback if ADK is unavailable
        try:
            while True:
                message = await websocket.receive()
                if "text" in message and message["text"]:
                    try:
                        data = json.loads(message["text"])
                        if data.get("type") in ("search", "catalog_search", "search_catalog"):
                            session_search_catalog(query=data.get("query"), category=data.get("category"))
                        elif data.get("type") in ("order", "order_placed", "place_order"):
                            session_place_order(
                                customer_name=data.get("customer_name") or "Customer",
                                product_id=int(data.get("product_id", 1)),
                                quantity=int(data.get("quantity", 1))
                            )
                    except Exception:
                        pass
        except (WebSocketDisconnect, RuntimeError):
            pass

    broadcaster_task.cancel()
    try:
        await broadcaster_task
    except asyncio.CancelledError:
        pass
