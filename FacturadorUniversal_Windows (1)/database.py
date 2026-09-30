import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).with_name("facturador.db")

class Database:
    def __init__(self, path=DB_PATH):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self._create()

    def _create(self):
        cur = self.conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            merchant TEXT,
            portal_url TEXT,
            raw_text TEXT,
            data_json TEXT,
            status TEXT DEFAULT 'Pendiente',
            error TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS learning (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descriptor TEXT NOT NULL,
            target_field TEXT NOT NULL,
            merchant TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            pdf_path TEXT,
            xml_path TEXT,
            uuid TEXT,
            status TEXT,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT,
            message TEXT,
            solution TEXT,
            merchant TEXT,
            created_at TEXT NOT NULL
        );
        """)
        self.conn.commit()

    def save_ticket(self, image_path, merchant, portal_url, raw_text, data, status="Pendiente", error=""):
        import json
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO tickets(image_path, merchant, portal_url, raw_text, data_json, status, error, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (image_path, merchant, portal_url, raw_text, json.dumps(data, ensure_ascii=False), status, error, datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()
        return cur.lastrowid

    def update_ticket(self, ticket_id, **kwargs):
        parts, vals = [], []
        for k, v in kwargs.items():
            parts.append(f"{k}=?")
            vals.append(v)
        vals.append(ticket_id)
        self.conn.execute(f"UPDATE tickets SET {', '.join(parts)} WHERE id=?", vals)
        self.conn.commit()

    def add_learning(self, descriptor, target_field, merchant=""):
        self.conn.execute(
            "INSERT INTO learning(descriptor, target_field, merchant, created_at) VALUES(?,?,?,?)",
            (descriptor, target_field, merchant, datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def get_learning(self):
        return self.conn.execute("SELECT * FROM learning ORDER BY id DESC").fetchall()

    def add_error(self, code, message, solution, merchant=""):
        self.conn.execute(
            "INSERT INTO errors(code, message, solution, merchant, created_at) VALUES(?,?,?,?,?)",
            (code, message, solution, merchant, datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def save_invoice(self, ticket_id, pdf_path="", xml_path="", uuid="", status="Generada"):
        self.conn.execute(
            "INSERT INTO invoices(ticket_id, pdf_path, xml_path, uuid, status, created_at) VALUES(?,?,?,?,?,?)",
            (ticket_id, pdf_path, xml_path, uuid, status, datetime.now().isoformat(timespec="seconds"))
        )
        self.conn.commit()

    def set(self, key, value):
        self.conn.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, value))
        self.conn.commit()

    def get(self, key, default=""):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default

    def close(self):
        self.conn.close()
