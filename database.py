import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import random

DB_FILE = "inventory.db"

def init_db():
    """Initialize the database with tables and dummy data if empty."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Products Table
    c.execute('''CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    manufacturer TEXT,
                    barcode TEXT UNIQUE,
                    stock INTEGER DEFAULT 0,
                    expiry TEXT,
                    min_stock INTEGER DEFAULT 5
                )''')
    
    # Orders Table
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    quantity INTEGER,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                )''')
    
    # Check if empty, if so, seed data
    c.execute("SELECT count(*) FROM products")
    if c.fetchone()[0] == 0:
        seed_data(c)
        
    conn.commit()
    conn.close()

def seed_data(cursor):
    """Seed the database with sample data."""
    sample_products = [
        ("No.11 メス刃", "フェザー", "4902470036647", 100, (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'), 20),
        ("3-0 ナイロン糸", "エチコン", "103001", 3, (datetime.now() + timedelta(days=100)).strftime('%Y-%m-%d'), 10),
        ("4-0 バイクリル", "エチコン", "104002", 50, (datetime.now() + timedelta(days=200)).strftime('%Y-%m-%d'), 10),
        ("ステープラー 35W", "3M", "888888", 2, (datetime.now() + timedelta(days=50)).strftime('%Y-%m-%d'), 5),
        ("吸収性止血材", "ジョンソン", "999999", 0, "2024-12-31", 5),
    ]
    cursor.executemany("INSERT INTO products (name, manufacturer, barcode, stock, expiry, min_stock) VALUES (?, ?, ?, ?, ?, ?)", sample_products)
    print("Database seeded with sample data.")

def get_inventory():
    """Fetch all inventory as a DataFrame."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()
    return df

def get_product(product_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE id = ?", (product_id,))
    row = c.fetchone()
    conn.close()
    return row

def get_product_by_barcode(barcode):
    """Find a product by barcode."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT * FROM products WHERE barcode = ?", (barcode,))
    row = c.fetchone()
    conn.close()
    if row:
        # Convert to dictionary for easier usage
        columns = [col[0] for col in c.description]
        return dict(zip(columns, row))
    return None

def update_stock(product_id, change):
    """Update stock count (positive or negative)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE products SET stock = stock + ? WHERE id = ?", (change, product_id))
    conn.commit()
    conn.close()

def add_to_order_list(product_id, quantity=1):
    """Add item to order list."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO orders (product_id, quantity) VALUES (?, ?)", (product_id, quantity))
    conn.commit()
    conn.close()

def get_orders():
    """Fetch current orders."""
    conn = sqlite3.connect(DB_FILE)
    query = '''
        SELECT o.id, p.name, p.manufacturer, o.quantity, o.status, o.created_at
        FROM orders o
        JOIN products p ON o.product_id = p.id
        WHERE o.status = 'pending'
        ORDER BY o.created_at DESC
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def clear_orders():
    """Clear all pending orders (mark as ordered)."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE orders SET status = 'ordered' WHERE status = 'pending'")
    conn.commit()
    conn.close()
