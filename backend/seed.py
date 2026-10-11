import sys
from pathlib import Path

# Ensure backend directory is on sys.path for direct script execution from any location
sys.path.insert(0, str(Path(__file__).resolve().parent))

from database import DB_PATH, get_db_connection

PRODUCTS_DATA = [
    {
        "id": 1,
        "title": "Wireless Noise-Canceling Headphones",
        "price": 199.99,
        "description": "Over-ear Bluetooth headphones with high-fidelity sound.",
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=500&auto=format&fit=crop"
    },
    {
        "id": 2,
        "title": "Ergonomic Wireless Mouse",
        "price": 49.99,
        "description": "Vertical ergonomic optical mouse with customizable buttons and multi-device connection.",
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1615663245857-ac93bb7c39e7?w=500&auto=format&fit=crop"
    },
    {
        "id": 3,
        "title": "Mechanical Gaming Keyboard",
        "price": 89.95,
        "description": "RGB backlit mechanical keyboard featuring tactile switches and durable aluminum frame.",
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=500&auto=format&fit=crop"
    },
    {
        "id": 4,
        "title": "4K Ultra HD Monitor 27-inch",
        "price": 349.00,
        "description": "IPS panel display with HDR10 support, ultra-thin bezels, and versatile USB-C connectivity.",
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=500&auto=format&fit=crop"
    },
    {
        "id": 5,
        "title": "Portable Bluetooth Speaker",
        "price": 68.50,
        "description": "Waterproof IPX7 portable speaker delivering deep bass and 12-hour continuous playback.",
        "category": "Electronics",
        "image": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=500&auto=format&fit=crop"
    },
    {
        "id": 6,
        "title": "Classic Organic Cotton Hoodie",
        "price": 55.00,
        "description": "Soft, heavyweight organic cotton pullover hoodie with front pouch pocket.",
        "category": "Apparel",
        "image": "https://images.unsplash.com/photo-1556905055-8f358a7a47b2?w=500&auto=format&fit=crop"
    },
    {
        "id": 7,
        "title": "Slim Fit Denim Jacket",
        "price": 78.20,
        "description": "Timeless blue denim trucker jacket with button closures and twin chest pockets.",
        "category": "Apparel",
        "image": "https://images.unsplash.com/photo-1576995853123-5a10305d93c0?w=500&auto=format&fit=crop"
    },
    {
        "id": 8,
        "title": "Breathable Athletic T-Shirt",
        "price": 29.99,
        "description": "Moisture-wicking quick-dry workout t-shirt for maximum comfort during training.",
        "category": "Apparel",
        "image": "https://images.unsplash.com/photo-1521572267360-ee0c2909d518?w=500&auto=format&fit=crop"
    },
    {
        "id": 9,
        "title": "Merino Wool Winter Scarf",
        "price": 42.00,
        "description": "Luxurious 100% merino wool scarf providing exceptional warmth and softness.",
        "category": "Apparel",
        "image": "https://images.unsplash.com/photo-1608256246200-53e635b5b65f?w=500&auto=format&fit=crop"
    },
    {
        "id": 10,
        "title": "Stainless Steel Gooseneck Kettle",
        "price": 45.99,
        "description": "Precision pour-over electric kettle with temperature control and warm-keep function.",
        "category": "Home & Kitchen",
        "image": "https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=500&auto=format&fit=crop"
    },
    {
        "id": 11,
        "title": "Cast Iron Dutch Oven 5-Quart",
        "price": 89.99,
        "description": "Enameled cast iron pot ideal for baking, braising, roasting, and slow cooking.",
        "category": "Home & Kitchen",
        "image": "https://images.unsplash.com/photo-1584992236310-6edddc08acff?w=500&auto=format&fit=crop"
    },
    {
        "id": 12,
        "title": "Automatic Espresso Machine",
        "price": 299.00,
        "description": "Compact espresso maker with built-in milk frother and 15-bar Italian pressure pump.",
        "category": "Home & Kitchen",
        "image": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=500&auto=format&fit=crop"
    },
    {
        "id": 13,
        "title": "Bamboo Cutting Board Set",
        "price": 32.50,
        "description": "Set of 3 organic bamboo cutting boards with juice grooves and easy-grip handles.",
        "category": "Home & Kitchen",
        "image": "https://images.unsplash.com/photo-1590794056226-79ef3a8147e1?w=500&auto=format&fit=crop"
    },
    {
        "id": 14,
        "title": "Non-Slip Yoga Mat",
        "price": 38.00,
        "description": "Eco-friendly TPE yoga mat with alignment line marks and carrying strap.",
        "category": "Fitness & Outdoors",
        "image": "https://images.unsplash.com/photo-1601925260368-ae2f83cf8b7f?w=500&auto=format&fit=crop"
    },
    {
        "id": 15,
        "title": "Adjustable Dumbbell Set",
        "price": 159.99,
        "description": "Space-saving adjustable weights ranging from 5 to 52.5 lbs with quick dial system.",
        "category": "Fitness & Outdoors",
        "image": "https://images.unsplash.com/photo-1638536532686-d610adfc8e5c?w=500&auto=format&fit=crop"
    },
    {
        "id": 16,
        "title": "Insulated Stainless Water Bottle",
        "price": 24.95,
        "description": "Double-wall vacuum insulated flask keeping drinks cold for 24 hours or hot for 12.",
        "category": "Fitness & Outdoors",
        "image": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=500&auto=format&fit=crop"
    },
    {
        "id": 17,
        "title": "Lightweight Camping Hammock",
        "price": 34.99,
        "description": "Heavy-duty nylon portable hammock complete with tree straps and carabiners.",
        "category": "Fitness & Outdoors",
        "image": "https://images.unsplash.com/photo-1510312305653-8ed496efae75?w=500&auto=format&fit=crop"
    },
    {
        "id": 18,
        "title": "Hardcover Leather Journal",
        "price": 18.50,
        "description": "240-page lined notebook crafted with premium thick paper and ribbon bookmark.",
        "category": "Books & Stationery",
        "image": "https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?w=500&auto=format&fit=crop"
    },
    {
        "id": 19,
        "title": "Fountain Pen Classic Edition",
        "price": 36.00,
        "description": "Elegant fine nib writing pen with ink converter and brass accent clip.",
        "category": "Books & Stationery",
        "image": "https://images.unsplash.com/photo-1583485088034-697b5bc54ccd?w=500&auto=format&fit=crop"
    },
    {
        "id": 20,
        "title": "Minimalist Desk Organizer",
        "price": 22.99,
        "description": "Natural wooden desk caddy with compartments for pens, notes, and smartphone.",
        "category": "Books & Stationery",
        "image": "https://images.unsplash.com/photo-1516962215378-7fa2e137ae93?w=500&auto=format&fit=crop"
    },
    {
        "id": 21,
        "title": "Architectural Photography Book",
        "price": 45.00,
        "description": "Hardcover coffee table book showcasing modern architecture across five continents.",
        "category": "Books & Stationery",
        "image": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=500&auto=format&fit=crop"
    },
    {
        "id": 22,
        "title": "Pro Running Sneakers",
        "price": 120.00,
        "description": "Lightweight road running shoes with responsive foam cushioning and breathable mesh.",
        "category": "Footwear",
        "image": "https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=500&auto=format&fit=crop"
    },
    {
        "id": 23,
        "title": "Leather Chelsea Boots",
        "price": 145.00,
        "description": "Genuine full-grain leather boots with elastic side panels and durable rubber soles.",
        "category": "Footwear",
        "image": "https://images.unsplash.com/photo-1638247025967-b4e38f787b76?w=500&auto=format&fit=crop"
    },
    {
        "id": 24,
        "title": "Casual Canvas Slip-On Shoes",
        "price": 48.00,
        "description": "Comfortable daily footwear featuring padded collars and flexible vulcanized soles.",
        "category": "Footwear",
        "image": "https://images.unsplash.com/photo-1525966222134-fcfa99b8ae77?w=500&auto=format&fit=crop"
    },
    {
        "id": 25,
        "title": "Trail Hiking Boots",
        "price": 135.50,
        "description": "Waterproof high-top hiking boots designed for rugged mountain terrains.",
        "category": "Footwear",
        "image": "https://images.unsplash.com/photo-1520639888713-7851133b1ed0?w=500&auto=format&fit=crop"
    }
]


def seed_database() -> int:
    """Drops table products if exists, creates table, seeds 25 items, commits, prints success count, and returns count."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Drop existing table
    cursor.execute("DROP TABLE IF EXISTS products")

    # Create table with exact schema required
    cursor.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            price REAL NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            image TEXT NOT NULL
        )
        """
    )

    # Insert 25 products
    for prod in PRODUCTS_DATA:
        cursor.execute(
            """
            INSERT INTO products (id, title, price, description, category, image)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                prod["id"],
                prod["title"],
                prod["price"],
                prod["description"],
                prod["category"],
                prod["image"],
            ),
        )

    conn.commit()

    # Verify inserted count
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    conn.close()

    print(f"Successfully seeded {count} products to {DB_PATH}")
    return count


if __name__ == "__main__":
    seed_database()
