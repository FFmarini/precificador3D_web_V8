import os
import sqlite3
from pathlib import Path


IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg")
STOCK_DEDUCT_STATUSES = {"Pronto", "Entregue", "Estoque"}
CLIENT_SORT_FIELDS = {
    "id": "id",
    "nome": "name",
    "telefone": "phone",
    "cidade": "city",
}
PROJECT_SORT_FIELDS = {
    "id": "id",
    "nome": "name",
    "url": "url",
}
FILAMENT_SORT_FIELDS = {
    "id": "id",
    "nome": "name",
    "marca": "brand",
    "tipo": "ftype",
    "cor": "color",
    "preco": "price_per_kg",
    "estoque": "stock_grams",
    "situacao": "stock_grams - min_stock_alert_grams",
}
ORDER_SORT_FIELDS = {
    "id": "o.id",
    "codigo": "o.order_no",
    "cliente": "client_name",
    "projeto": "project_name",
    "status": "o.status",
    "valor": "o.final_price",
    "pago": "o.is_paid",
    "data": "o.created_at",
    "filamento": "filament_name",
}


def get_db_path() -> Path:
    configured = os.environ.get("PREC_DB_PATH")
    if configured:
        return Path(configured).resolve()
    if os.name == "nt":
        local_dir = Path(os.environ.get("TEMP", Path.cwd())) / "PrecificadorWeb"
        local_dir.mkdir(parents=True, exist_ok=True)
        return (local_dir / "precificador.db").resolve()
    return Path("data/precificador.db").resolve()


def db_connect():
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys=ON;")
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con


def ensure_column(con, table: str, col: str, definition: str):
    cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")


def ensure_created_at(con, table: str):
    cols = [r["name"] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]
    if "created_at" not in cols:
        con.execute(f"ALTER TABLE {table} ADD COLUMN created_at TEXT")
        con.execute(
            f"UPDATE {table} SET created_at=datetime('now') "
            "WHERE created_at IS NULL OR created_at=''"
        )


def rows_to_dicts(rows):
    return [dict(r) for r in rows]


def to_float(value, default=0.0):
    try:
        return float(value or default)
    except Exception:
        return float(default)


def normalize_direction(direction: str) -> str:
    return "DESC" if str(direction or "").lower() == "desc" else "ASC"


def like_term(search: str) -> str:
    return f"%{str(search or '').strip()}%"


def infer_project_thumbnail(url: str, thumbnail_url: str | None = None) -> str | None:
    thumbnail = str(thumbnail_url or "").strip()
    if thumbnail:
        return thumbnail
    candidate = str(url or "").strip()
    lowered = candidate.lower()
    if lowered.startswith(("http://", "https://")) and any(lowered.endswith(ext) for ext in IMAGE_EXTENSIONS):
        return candidate
    return None


def compute_stock_status(stock_grams: float, min_stock_alert_grams: float) -> str:
    stock_grams = to_float(stock_grams)
    min_stock_alert_grams = max(to_float(min_stock_alert_grams), 0.0)
    if stock_grams <= 0:
        return "ESGOTADO"
    if stock_grams <= min_stock_alert_grams:
        return "BAIXO"
    return "OK"


def decorate_filament_stock(item: dict) -> dict:
    stock_grams = to_float(item.get("stock_grams"))
    min_stock_alert_grams = to_float(item.get("min_stock_alert_grams"), 200.0)
    status = compute_stock_status(stock_grams, min_stock_alert_grams)
    item["stock_grams"] = stock_grams
    item["min_stock_alert_grams"] = min_stock_alert_grams
    item["spool_weight_grams"] = to_float(item.get("spool_weight_grams"), 1000.0)
    item["stock_status"] = status
    item["stock_status_class"] = {
        "OK": "badge-ok",
        "BAIXO": "badge-low",
        "ESGOTADO": "badge-out",
    }[status]
    return item


def db_init():
    con = db_connect()

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS order_seq (
            id INTEGER PRIMARY KEY CHECK(id=1),
            last_order_no INTEGER NOT NULL
        )
        """
    )
    con.execute("INSERT OR IGNORE INTO order_seq(id,last_order_no) VALUES(1,0)")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            instagram TEXT,
            city TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    ensure_column(con, "clients", "notes", "TEXT")
    ensure_created_at(con, "clients")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS filaments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            brand TEXT,
            ftype TEXT,
            color TEXT,
            code TEXT,
            price_per_kg REAL,
            notes TEXT,
            stock_grams REAL NOT NULL DEFAULT 0,
            min_stock_alert_grams REAL NOT NULL DEFAULT 200,
            spool_weight_grams REAL NOT NULL DEFAULT 1000,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    for col, definition in [
        ("brand", "TEXT"),
        ("ftype", "TEXT"),
        ("color", "TEXT"),
        ("code", "TEXT"),
        ("price_per_kg", "REAL"),
        ("notes", "TEXT"),
        ("stock_grams", "REAL NOT NULL DEFAULT 0"),
        ("min_stock_alert_grams", "REAL NOT NULL DEFAULT 200"),
        ("spool_weight_grams", "REAL NOT NULL DEFAULT 1000"),
    ]:
        ensure_column(con, "filaments", col, definition)
    ensure_created_at(con, "filaments")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT,
            thumbnail_url TEXT,
            notes TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    ensure_column(con, "projects", "url", "TEXT")
    ensure_column(con, "projects", "thumbnail_url", "TEXT")
    ensure_column(con, "projects", "notes", "TEXT")
    ensure_created_at(con, "projects")

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            client_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            filament_id INTEGER,
            pieces INTEGER NOT NULL,
            time_seconds_per_piece INTEGER NOT NULL DEFAULT 0,
            filament_g_per_piece REAL NOT NULL DEFAULT 0,
            chosen_color TEXT,
            status TEXT NOT NULL DEFAULT 'Orçado',
            payment_method TEXT NOT NULL DEFAULT 'Pix',
            is_paid INTEGER NOT NULL DEFAULT 0,
            notes TEXT,
            filament_price_per_kg REAL NOT NULL DEFAULT 0,
            energy_price_per_kwh REAL NOT NULL DEFAULT 0,
            printer_avg_watts REAL NOT NULL DEFAULT 0,
            machine_cost_per_hour REAL NOT NULL DEFAULT 0,
            labor_cost_fixed REAL NOT NULL DEFAULT 0,
            margin_percent REAL NOT NULL DEFAULT 0,
            round_to REAL NOT NULL DEFAULT 1,
            failure_rate_percent REAL NOT NULL DEFAULT 5,
            overhead_percent REAL NOT NULL DEFAULT 10,
            packaging_cost REAL NOT NULL DEFAULT 0,
            platform_fee_percent REAL NOT NULL DEFAULT 0,
            payment_fee_percent REAL NOT NULL DEFAULT 0,
            shipping_price REAL NOT NULL DEFAULT 0,
            discount_value REAL NOT NULL DEFAULT 0,
            total_cost REAL NOT NULL DEFAULT 0,
            product_price REAL NOT NULL DEFAULT 0,
            fees_estimated REAL NOT NULL DEFAULT 0,
            profit REAL NOT NULL DEFAULT 0,
            final_price REAL NOT NULL DEFAULT 0,
            stock_discounted INTEGER NOT NULL DEFAULT 0,
            stock_discounted_grams REAL NOT NULL DEFAULT 0
        )
        """
    )
    for col, definition in [
        ("chosen_color", "TEXT"),
        ("notes", "TEXT"),
        ("status", "TEXT DEFAULT 'Orçado'"),
        ("payment_method", "TEXT DEFAULT 'Pix'"),
        ("is_paid", "INTEGER NOT NULL DEFAULT 0"),
        ("filament_price_per_kg", "REAL NOT NULL DEFAULT 0"),
        ("energy_price_per_kwh", "REAL NOT NULL DEFAULT 0"),
        ("printer_avg_watts", "REAL NOT NULL DEFAULT 0"),
        ("machine_cost_per_hour", "REAL NOT NULL DEFAULT 0"),
        ("labor_cost_fixed", "REAL NOT NULL DEFAULT 0"),
        ("margin_percent", "REAL NOT NULL DEFAULT 0"),
        ("round_to", "REAL NOT NULL DEFAULT 1"),
        ("failure_rate_percent", "REAL NOT NULL DEFAULT 5"),
        ("overhead_percent", "REAL NOT NULL DEFAULT 10"),
        ("packaging_cost", "REAL NOT NULL DEFAULT 0"),
        ("platform_fee_percent", "REAL NOT NULL DEFAULT 0"),
        ("payment_fee_percent", "REAL NOT NULL DEFAULT 0"),
        ("shipping_price", "REAL NOT NULL DEFAULT 0"),
        ("discount_value", "REAL NOT NULL DEFAULT 0"),
        ("total_cost", "REAL NOT NULL DEFAULT 0"),
        ("product_price", "REAL NOT NULL DEFAULT 0"),
        ("fees_estimated", "REAL NOT NULL DEFAULT 0"),
        ("profit", "REAL NOT NULL DEFAULT 0"),
        ("final_price", "REAL NOT NULL DEFAULT 0"),
        ("time_seconds_per_piece", "INTEGER NOT NULL DEFAULT 0"),
        ("filament_g_per_piece", "REAL NOT NULL DEFAULT 0"),
        ("stock_discounted", "INTEGER NOT NULL DEFAULT 0"),
        ("stock_discounted_grams", "REAL NOT NULL DEFAULT 0"),
    ]:
        ensure_column(con, "orders", col, definition)

    cols = [r["name"] for r in con.execute("PRAGMA table_info(orders)").fetchall()]
    if "created_at" not in cols:
        con.execute("ALTER TABLE orders ADD COLUMN created_at TEXT")
    con.execute(
        "UPDATE orders SET created_at=datetime('now') "
        "WHERE created_at IS NULL OR created_at=''"
    )

    con.execute(
        """
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filament_id INTEGER NOT NULL,
            order_id INTEGER,
            movement_type TEXT NOT NULL,
            grams REAL NOT NULL,
            notes TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY(filament_id) REFERENCES filaments(id) ON DELETE RESTRICT,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE SET NULL
        )
        """
    )
    ensure_created_at(con, "stock_movements")

    con.commit()
    con.close()


def get_setting(key: str):
    con = db_connect()
    row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    con.close()
    return row["value"] if row else None


def set_setting(key: str, value):
    con = db_connect()
    if value is None or str(value).strip() == "":
        con.execute("DELETE FROM settings WHERE key=?", (key,))
    else:
        con.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)),
        )
    con.commit()
    con.close()


def next_order_no():
    con = db_connect()
    last = int(con.execute("SELECT last_order_no FROM order_seq WHERE id=1").fetchone()[0])
    new = last + 1
    con.execute("UPDATE order_seq SET last_order_no=? WHERE id=1", (new,))
    con.commit()
    con.close()
    return new


def format_order_code(order_no: int):
    return f"TD-{int(order_no):06d}"


def list_clients(search="", sort="nome", direction="asc"):
    con = db_connect()
    sql = "SELECT * FROM clients"
    params = []
    if str(search or "").strip():
        term = like_term(search)
        sql += """
            WHERE CAST(id AS TEXT) LIKE ?
               OR name LIKE ?
               OR COALESCE(phone,'') LIKE ?
               OR COALESCE(city,'') LIKE ?
               OR COALESCE(notes,'') LIKE ?
        """
        params.extend([term, term, term, term, term])
    order_by = CLIENT_SORT_FIELDS.get(sort, CLIENT_SORT_FIELDS["nome"])
    sql += f" ORDER BY {order_by} {normalize_direction(direction)}, id DESC"
    rows = con.execute(sql, tuple(params)).fetchall()
    con.close()
    return rows_to_dicts(rows)


def get_client(client_id: int):
    con = db_connect()
    row = con.execute("SELECT * FROM clients WHERE id=?", (client_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def save_client(data: dict, client_id=None):
    con = db_connect()
    vals = (
        data.get("name"),
        data.get("phone"),
        data.get("instagram"),
        data.get("city"),
        data.get("notes"),
    )
    if client_id:
        con.execute(
            "UPDATE clients SET name=?, phone=?, instagram=?, city=?, notes=? WHERE id=?",
            vals + (client_id,),
        )
    else:
        con.execute(
            "INSERT INTO clients(name,phone,instagram,city,notes,created_at) "
            "VALUES(?,?,?,?,?,datetime('now'))",
            vals,
        )
    con.commit()
    con.close()


def delete_client(client_id: int):
    con = db_connect()
    con.execute("DELETE FROM clients WHERE id=?", (client_id,))
    con.commit()
    con.close()


def list_filaments(search="", sort="nome", direction="asc"):
    con = db_connect()
    sql = """
        SELECT id,name,brand,ftype,color,code,price_per_kg,notes,
               stock_grams,min_stock_alert_grams,spool_weight_grams,created_at
        FROM filaments
    """
    params = []
    if str(search or "").strip():
        term = like_term(search)
        sql += """
            WHERE CAST(id AS TEXT) LIKE ?
               OR name LIKE ?
               OR COALESCE(brand,'') LIKE ?
               OR COALESCE(ftype,'') LIKE ?
               OR COALESCE(color,'') LIKE ?
               OR COALESCE(code,'') LIKE ?
               OR COALESCE(notes,'') LIKE ?
        """
        params.extend([term, term, term, term, term, term, term])
    order_by = FILAMENT_SORT_FIELDS.get(sort, FILAMENT_SORT_FIELDS["nome"])
    sql += f" ORDER BY {order_by} {normalize_direction(direction)}, name ASC"
    rows = con.execute(sql, tuple(params)).fetchall()
    con.close()
    return [decorate_filament_stock(dict(row)) for row in rows]


def get_filament(fid: int):
    con = db_connect()
    row = con.execute("SELECT * FROM filaments WHERE id=?", (fid,)).fetchone()
    con.close()
    return decorate_filament_stock(dict(row)) if row else None


def save_filament(data: dict, filament_id=None):
    con = db_connect()
    vals = (
        data.get("name"),
        data.get("brand"),
        data.get("ftype"),
        data.get("color"),
        data.get("code"),
        to_float(data.get("price_per_kg")),
        data.get("notes"),
        to_float(data.get("stock_grams")),
        to_float(data.get("min_stock_alert_grams"), 200.0),
        to_float(data.get("spool_weight_grams"), 1000.0),
    )
    if filament_id:
        con.execute(
            """
            UPDATE filaments
            SET name=?,brand=?,ftype=?,color=?,code=?,price_per_kg=?,notes=?,
                stock_grams=?,min_stock_alert_grams=?,spool_weight_grams=?
            WHERE id=?
            """,
            vals + (filament_id,),
        )
    else:
        con.execute(
            """
            INSERT INTO filaments(
                name,brand,ftype,color,code,price_per_kg,notes,
                stock_grams,min_stock_alert_grams,spool_weight_grams,created_at
            )
            VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))
            """,
            vals,
        )
    con.commit()
    con.close()


def delete_filament(fid: int):
    con = db_connect()
    con.execute("DELETE FROM filaments WHERE id=?", (fid,))
    con.commit()
    con.close()


def list_projects(search="", sort="nome", direction="asc"):
    con = db_connect()
    sql = "SELECT * FROM projects"
    params = []
    if str(search or "").strip():
        term = like_term(search)
        sql += """
            WHERE CAST(id AS TEXT) LIKE ?
               OR name LIKE ?
               OR COALESCE(url,'') LIKE ?
               OR COALESCE(thumbnail_url,'') LIKE ?
               OR COALESCE(notes,'') LIKE ?
        """
        params.extend([term, term, term, term, term])
    order_by = PROJECT_SORT_FIELDS.get(sort, PROJECT_SORT_FIELDS["nome"])
    sql += f" ORDER BY {order_by} {normalize_direction(direction)}, id DESC"
    rows = con.execute(sql, tuple(params)).fetchall()
    con.close()
    return rows_to_dicts(rows)


def get_project(project_id: int):
    con = db_connect()
    row = con.execute("SELECT * FROM projects WHERE id=?", (project_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def save_project(data: dict, project_id=None):
    con = db_connect()
    vals = (
        data.get("name"),
        data.get("url"),
        infer_project_thumbnail(data.get("url"), data.get("thumbnail_url")),
        data.get("notes"),
    )
    if project_id:
        con.execute(
            "UPDATE projects SET name=?,url=?,thumbnail_url=?,notes=? WHERE id=?",
            vals + (project_id,),
        )
    else:
        con.execute(
            "INSERT INTO projects(name,url,thumbnail_url,notes,created_at) VALUES(?,?,?,?,datetime('now'))",
            vals,
        )
    con.commit()
    con.close()


def delete_project(project_id: int):
    con = db_connect()
    con.execute("DELETE FROM projects WHERE id=?", (project_id,))
    con.commit()
    con.close()


def list_orders(status=None, view="active", search="", sort="id", direction="desc"):
    con = db_connect()
    sql = """
        SELECT o.*, c.name AS client_name, p.name AS project_name,
               COALESCE(f.name,'') AS filament_name
        FROM orders o
        JOIN clients c ON c.id=o.client_id
        JOIN projects p ON p.id=o.project_id
        LEFT JOIN filaments f ON f.id=o.filament_id
    """
    where = []
    params = []
    if status and status != "Todos":
        where.append("o.status=?")
        params.append(status)
    elif view == "stock":
        where.append("o.status='Estoque'")
    elif view == "history":
        where.append("o.status IN ('Entregue','Cancelado')")
    else:
        where.append("o.status NOT IN ('Estoque','Entregue','Cancelado')")

    if str(search or "").strip():
        term = like_term(search)
        where.append(
            """(
                CAST(o.id AS TEXT) LIKE ?
                OR CAST(o.order_no AS TEXT) LIKE ?
                OR c.name LIKE ?
                OR p.name LIKE ?
                OR COALESCE(f.name,'') LIKE ?
                OR COALESCE(o.status,'') LIKE ?
                OR COALESCE(o.payment_method,'') LIKE ?
            )"""
        )
        params.extend([term, term, term, term, term, term, term])

    if where:
        sql += " WHERE " + " AND ".join(where)

    order_by = ORDER_SORT_FIELDS.get(sort, ORDER_SORT_FIELDS["id"])
    sql += f" ORDER BY {order_by} {normalize_direction(direction)}, o.id DESC"
    rows = con.execute(sql, tuple(params)).fetchall()
    con.close()
    data = []
    for row in rows:
        item = dict(row)
        item["code"] = format_order_code(item["order_no"])
        item["stock_discounted"] = int(item.get("stock_discounted") or 0)
        item["stock_discounted_grams"] = to_float(item.get("stock_discounted_grams"))
        item["is_budget_status"] = str(item.get("status") or "").strip().lower().startswith("or")
        data.append(item)
    return data


def list_client_receipt_orders(client_id: int, receipt_status="Pronto"):
    con = db_connect()
    sql = """
        SELECT o.*, c.name AS client_name, p.name AS project_name,
               COALESCE(f.name,'') AS filament_name
        FROM orders o
        JOIN clients c ON c.id=o.client_id
        JOIN projects p ON p.id=o.project_id
        LEFT JOIN filaments f ON f.id=o.filament_id
        WHERE o.client_id=?
    """
    params = [client_id]
    if str(receipt_status or "").strip():
        sql += " AND COALESCE(o.status,'') = ?"
        params.append(str(receipt_status).strip())
    sql += " ORDER BY o.created_at ASC, o.id ASC"
    rows = con.execute(sql, tuple(params)).fetchall()
    con.close()
    data = []
    for row in rows:
        item = dict(row)
        item["code"] = format_order_code(item["order_no"])
        item["final_price"] = to_float(item.get("final_price"))
        item["is_paid"] = int(item.get("is_paid") or 0)
        item["pieces"] = int(item.get("pieces") or 0)
        data.append(item)
    return data


def get_order(order_id: int):
    con = db_connect()
    row = con.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    con.close()
    if not row:
        return None
    item = dict(row)
    item["stock_discounted"] = int(item.get("stock_discounted") or 0)
    item["stock_discounted_grams"] = to_float(item.get("stock_discounted_grams"))
    return item


def save_order(data: dict, order_id=None):
    con = db_connect()
    fields = [
        "client_id",
        "project_id",
        "filament_id",
        "pieces",
        "time_seconds_per_piece",
        "filament_g_per_piece",
        "chosen_color",
        "status",
        "payment_method",
        "is_paid",
        "notes",
        "filament_price_per_kg",
        "energy_price_per_kwh",
        "printer_avg_watts",
        "machine_cost_per_hour",
        "labor_cost_fixed",
        "margin_percent",
        "round_to",
        "failure_rate_percent",
        "overhead_percent",
        "packaging_cost",
        "platform_fee_percent",
        "payment_fee_percent",
        "shipping_price",
        "discount_value",
        "total_cost",
        "product_price",
        "fees_estimated",
        "profit",
        "final_price",
    ]
    values = [data.get(field) for field in fields]
    if order_id:
        set_clause = ",".join([f"{field}=?" for field in fields])
        con.execute(f"UPDATE orders SET {set_clause} WHERE id=?", values + [order_id])
        saved_id = int(order_id)
    else:
        order_no = next_order_no()
        cur = con.execute(
            f"INSERT INTO orders(order_no,created_at,{','.join(fields)}) "
            f"VALUES(?,datetime('now'),{','.join(['?'] * len(fields))})",
            [order_no] + values,
        )
        saved_id = int(cur.lastrowid)
    con.commit()
    con.close()
    return saved_id


def delete_order(order_id: int):
    con = db_connect()
    con.execute("DELETE FROM orders WHERE id=?", (order_id,))
    con.commit()
    con.close()


def _insert_stock_movement(con, filament_id: int, grams: float, movement_type: str, notes="", order_id=None):
    con.execute(
        """
        INSERT INTO stock_movements(filament_id,order_id,movement_type,grams,notes,created_at)
        VALUES(?,?,?,?,?,datetime('now'))
        """,
        (filament_id, order_id, movement_type, grams, notes or None),
    )


def add_filament_stock(fid: int, grams: float, notes="", order_id=None):
    grams = max(to_float(grams), 0.0)
    if grams <= 0:
        return None
    con = db_connect()
    con.execute("UPDATE filaments SET stock_grams = stock_grams + ? WHERE id=?", (grams, fid))
    _insert_stock_movement(con, fid, grams, "ENTRY", notes=notes, order_id=order_id)
    con.commit()
    con.close()
    return grams


def adjust_filament_stock(fid: int, grams: float, notes="", order_id=None):
    grams = to_float(grams)
    if grams == 0:
        return None
    con = db_connect()
    con.execute("UPDATE filaments SET stock_grams = stock_grams + ? WHERE id=?", (grams, fid))
    _insert_stock_movement(con, fid, grams, "ADJUSTMENT", notes=notes, order_id=order_id)
    con.commit()
    con.close()
    return grams


def list_stock_movements(fid=None, limit=100):
    con = db_connect()
    sql = """
        SELECT sm.*, f.name AS filament_name,
               o.order_no,
               c.name AS client_name
        FROM stock_movements sm
        JOIN filaments f ON f.id=sm.filament_id
        LEFT JOIN orders o ON o.id=sm.order_id
        LEFT JOIN clients c ON c.id=o.client_id
    """
    params = []
    if fid:
        sql += " WHERE sm.filament_id=?"
        params.append(fid)
    sql += " ORDER BY sm.id DESC LIMIT ?"
    params.append(int(limit))
    rows = con.execute(sql, tuple(params)).fetchall()
    con.close()
    data = []
    for row in rows:
        item = dict(row)
        if item.get("order_no") is not None:
            item["order_code"] = format_order_code(item["order_no"])
        else:
            item["order_code"] = ""
        data.append(item)
    return data


def get_low_stock_filaments():
    return [
        item
        for item in list_filaments()
        if item["stock_status"] in {"BAIXO", "ESGOTADO"}
    ]


def order_consumes_stock(order: dict) -> bool:
    return bool(order.get("filament_id")) and (order.get("status") in STOCK_DEDUCT_STATUSES)


def process_order_stock(order_id: int):
    order = get_order(order_id)
    if not order:
        return {"action": "missing"}
    if int(order.get("stock_discounted") or 0):
        return {"action": "already_discounted", "order": order}
    if not order_consumes_stock(order):
        return {"action": "ignored", "order": order}

    grams = max(to_float(order.get("pieces")) * to_float(order.get("filament_g_per_piece")), 0.0)
    if grams <= 0:
        return {"action": "ignored", "order": order}

    con = db_connect()
    con.execute(
        "UPDATE filaments SET stock_grams = stock_grams - ? WHERE id=?",
        (grams, order["filament_id"]),
    )
    _insert_stock_movement(
        con,
        order["filament_id"],
        -grams,
        "CONSUMPTION",
        notes=f"Baixa automática do pedido {format_order_code(order['order_no'])}",
        order_id=order_id,
    )
    con.execute(
        "UPDATE orders SET stock_discounted=1, stock_discounted_grams=? WHERE id=?",
        (grams, order_id),
    )
    con.commit()
    con.close()
    return {"action": "discounted", "grams": grams, "order": get_order(order_id)}
