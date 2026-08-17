from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class BusinessOperations:
    """Persistent business operations store for Ameer.

    Covers the operational core needed for a center/store management system:
    products, inventory, employees, customers, bookings, and orders.
    Data lives under AMEER_DATA_DIR when configured so Railway deployments do
    not wipe the business state.
    """

    def __init__(self, workspace_root: str | Path) -> None:
        root = Path(workspace_root).resolve()
        raw_data = (os.getenv("AMEER_DATA_DIR") or "").strip()
        if raw_data:
            data_dir = Path(raw_data).resolve()
            if data_dir.name != ".ameer":
                data_dir = data_dir / ".ameer"
        else:
            data_dir = root / ".ameer"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = data_dir / "business.sqlite3"
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS center_profile (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL,
                    timezone TEXT NOT NULL DEFAULT 'Asia/Riyadh',
                    currency TEXT NOT NULL DEFAULT 'SAR',
                    settings_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sku TEXT UNIQUE,
                    name TEXT NOT NULL,
                    price REAL NOT NULL DEFAULT 0,
                    stock REAL NOT NULL DEFAULT 0,
                    reorder_level REAL NOT NULL DEFAULT 0,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS inventory_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    delta REAL NOT NULL,
                    reason TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                );
                CREATE TABLE IF NOT EXISTS employees (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT,
                    phone TEXT,
                    email TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    phone TEXT,
                    email TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS bookings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    title TEXT NOT NULL,
                    starts_at TEXT NOT NULL,
                    ends_at TEXT,
                    employee_id INTEGER,
                    status TEXT NOT NULL DEFAULT 'confirmed',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(customer_id) REFERENCES customers(id),
                    FOREIGN KEY(employee_id) REFERENCES employees(id)
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER,
                    total REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'open',
                    notes TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(customer_id) REFERENCES customers(id)
                );
                """
            )
            now = _now()
            conn.execute(
                "INSERT OR IGNORE INTO center_profile(id,name,timezone,currency,settings_json,created_at,updated_at) VALUES(1,?,?,?,?,?,?)",
                ("مركز حلم الندى", "Asia/Riyadh", "SAR", "{}", now, now),
            )

    def center_profile(self) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM center_profile WHERE id=1").fetchone()
        return dict(row) if row else {"id": 1, "name": "مركز حلم الندى", "timezone": "Asia/Riyadh", "currency": "SAR", "settings_json": "{}"}

    def add_product(self, name: str, *, sku: str = "", price: float = 0, stock: float = 0, reorder_level: float = 0) -> Dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO products(sku,name,price,stock,reorder_level,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                (sku or None, name, float(price), float(stock), float(reorder_level), now, now),
            )
            product_id = int(cur.lastrowid)
        return self.get_product(product_id)

    def get_product(self, product_id: int) -> Dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM products WHERE id=?", (int(product_id),)).fetchone()
        if row is None:
            raise KeyError(f"product_not_found:{product_id}")
        return dict(row)

    def list_products(self, *, active_only: bool = True) -> List[Dict[str, Any]]:
        query = "SELECT * FROM products"
        args: tuple = ()
        if active_only:
            query += " WHERE active=1"
        query += " ORDER BY name"
        with self._connect() as conn:
            return [dict(r) for r in conn.execute(query, args).fetchall()]

    def adjust_stock(self, product_id: int, delta: float, *, reason: str = "manual") -> Dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            row = conn.execute("SELECT stock FROM products WHERE id=?", (int(product_id),)).fetchone()
            if row is None:
                raise KeyError(f"product_not_found:{product_id}")
            new_stock = float(row["stock"]) + float(delta)
            conn.execute("UPDATE products SET stock=?, updated_at=? WHERE id=?", (new_stock, now, int(product_id)))
            conn.execute(
                "INSERT INTO inventory_movements(product_id,delta,reason,created_at) VALUES(?,?,?,?)",
                (int(product_id), float(delta), reason, now),
            )
        return self.get_product(product_id)

    def low_stock(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM products WHERE active=1 AND stock <= reorder_level ORDER BY stock ASC"
            ).fetchall()
        return [dict(r) for r in rows]

    def add_employee(self, name: str, *, role: str = "", phone: str = "", email: str = "") -> Dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO employees(name,role,phone,email,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (name, role, phone, email, now, now),
            )
            employee_id = int(cur.lastrowid)
            row = conn.execute("SELECT * FROM employees WHERE id=?", (employee_id,)).fetchone()
        return dict(row)

    def list_employees(self, *, status: Optional[str] = "active") -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute("SELECT * FROM employees WHERE status=? ORDER BY name", (status,)).fetchall()
            else:
                rows = conn.execute("SELECT * FROM employees ORDER BY name").fetchall()
        return [dict(r) for r in rows]

    def add_customer(self, name: str, *, phone: str = "", email: str = "", notes: str = "") -> Dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO customers(name,phone,email,notes,created_at,updated_at) VALUES(?,?,?,?,?,?)",
                (name, phone, email, notes, now, now),
            )
            customer_id = int(cur.lastrowid)
            row = conn.execute("SELECT * FROM customers WHERE id=?", (customer_id,)).fetchone()
        return dict(row)

    def list_customers(self, *, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM customers ORDER BY name LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def create_booking(
        self,
        title: str,
        starts_at: str,
        *,
        ends_at: str = "",
        customer_id: Optional[int] = None,
        employee_id: Optional[int] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO bookings(customer_id,title,starts_at,ends_at,employee_id,notes,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (customer_id, title, starts_at, ends_at or None, employee_id, notes, now, now),
            )
            booking_id = int(cur.lastrowid)
            row = conn.execute("SELECT * FROM bookings WHERE id=?", (booking_id,)).fetchone()
        return dict(row)

    def list_bookings(self, *, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM bookings WHERE status=? ORDER BY starts_at LIMIT ?", (status, int(limit))
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM bookings ORDER BY starts_at LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]

    def create_order(self, *, customer_id: Optional[int] = None, total: float = 0, notes: str = "") -> Dict[str, Any]:
        now = _now()
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO orders(customer_id,total,notes,created_at,updated_at) VALUES(?,?,?,?,?)",
                (customer_id, float(total), notes, now, now),
            )
            order_id = int(cur.lastrowid)
            row = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
        return dict(row)

    def store_dashboard(self) -> Dict[str, Any]:
        return {"center": self.center_profile(), "modules": ["inventory", "employees", "bookings", "customers", "orders", "reports"], "dashboard": self.dashboard()}

    def dashboard(self) -> Dict[str, Any]:
        with self._connect() as conn:
            products = conn.execute("SELECT COUNT(*) c FROM products WHERE active=1").fetchone()["c"]
            employees = conn.execute("SELECT COUNT(*) c FROM employees WHERE status='active'").fetchone()["c"]
            bookings = conn.execute("SELECT COUNT(*) c FROM bookings WHERE status='confirmed'").fetchone()["c"]
            open_orders = conn.execute("SELECT COUNT(*) c FROM orders WHERE status='open'").fetchone()["c"]
        return {
            "products": int(products),
            "employees": int(employees),
            "confirmed_bookings": int(bookings),
            "open_orders": int(open_orders),
            "low_stock": self.low_stock(),
        }
