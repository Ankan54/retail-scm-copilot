#!/usr/bin/env python3
"""
Load all synthetic CSV data into a SQLite database.
Creates proper schema with types, PKs, FKs, and indexes.
"""

import csv
import os
import sqlite3
from pathlib import Path

# ──────────── Paths ────────────
SCRIPT_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
CSV_DIR = SCRIPT_DIR.parent / "data" / "synthetic"
DB_PATH = SCRIPT_DIR.parent / "data" / "supplychain.db"

# ──────────── Schema definitions ────────────
# Each table: (csv_name, pk_column, CREATE TABLE SQL)
# Tables are ordered so that FK targets are created before referencing tables.

SCHEMA = [
    # ─── Reference / master tables (no FK deps) ───
    ("territories", """
        CREATE TABLE IF NOT EXISTS territories (
            territory_id   TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            region         TEXT,
            state          TEXT,
            parent_territory_id TEXT,
            is_active      INTEGER DEFAULT 1,
            created_at     TEXT,
            updated_at     TEXT
        )
    """),
    ("product_categories", """
        CREATE TABLE IF NOT EXISTS product_categories (
            category_id        TEXT PRIMARY KEY,
            name               TEXT NOT NULL,
            parent_category_id TEXT,
            description        TEXT,
            is_active          INTEGER DEFAULT 1,
            created_at         TEXT
        )
    """),
    ("hsn_codes", """
        CREATE TABLE IF NOT EXISTS hsn_codes (
            hsn_code       TEXT PRIMARY KEY,
            description    TEXT,
            gst_rate       REAL,
            cgst_rate      REAL,
            sgst_rate      REAL,
            igst_rate      REAL,
            cess_rate      REAL,
            effective_from TEXT,
            effective_to   TEXT,
            created_at     TEXT
        )
    """),
    ("system_settings", """
        CREATE TABLE IF NOT EXISTS system_settings (
            setting_key   TEXT PRIMARY KEY,
            setting_value TEXT,
            setting_type  TEXT,
            description   TEXT
        )
    """),
    ("consumption_config", """
        CREATE TABLE IF NOT EXISTS consumption_config (
            config_id             TEXT PRIMARY KEY,
            product_id            TEXT,
            dealer_id             TEXT,
            backward_days         INTEGER,
            forward_days          INTEGER,
            direction_priority    TEXT,
            quantity_tolerance_pct INTEGER,
            expire_after_days     INTEGER,
            effective_from        TEXT,
            effective_to          TEXT,
            created_at            TEXT
        )
    """),

    # ─── Sales persons (self-referencing FK for manager) ───
    ("sales_persons", """
        CREATE TABLE IF NOT EXISTS sales_persons (
            sales_person_id TEXT PRIMARY KEY,
            employee_code   TEXT UNIQUE NOT NULL,
            name            TEXT NOT NULL,
            email           TEXT,
            phone           TEXT,
            role            TEXT,
            manager_id      TEXT REFERENCES sales_persons(sales_person_id),
            telegram_user_id TEXT,
            telegram_chat_id TEXT,
            is_active       INTEGER DEFAULT 1,
            date_of_joining TEXT,
            created_at      TEXT,
            updated_at      TEXT
        )
    """),
    ("territory_assignments", """
        CREATE TABLE IF NOT EXISTS territory_assignments (
            assignment_id   TEXT PRIMARY KEY,
            sales_person_id TEXT NOT NULL REFERENCES sales_persons(sales_person_id),
            territory_id    TEXT NOT NULL REFERENCES territories(territory_id),
            is_primary      INTEGER DEFAULT 1,
            assigned_date   TEXT,
            end_date        TEXT
        )
    """),

    # ─── Products & Warehouses ───
    ("products", """
        CREATE TABLE IF NOT EXISTS products (
            product_id        TEXT PRIMARY KEY,
            product_code      TEXT UNIQUE NOT NULL,
            name              TEXT NOT NULL,
            short_name        TEXT,
            description       TEXT,
            category_id       TEXT REFERENCES product_categories(category_id),
            brand             TEXT,
            hsn_code          TEXT REFERENCES hsn_codes(hsn_code),
            mrp               REAL,
            unit_price        REAL,
            dealer_price      REAL,
            distributor_price REAL,
            unit_of_measure   TEXT,
            units_per_case    INTEGER,
            min_order_qty     INTEGER,
            reorder_level     INTEGER,
            safety_stock      INTEGER,
            lead_time_days    INTEGER,
            is_manufactured   INTEGER,
            status            TEXT DEFAULT 'ACTIVE',
            launch_date       TEXT,
            discontinue_date  TEXT,
            created_at        TEXT,
            updated_at        TEXT
        )
    """),
    ("warehouses", """
        CREATE TABLE IF NOT EXISTS warehouses (
            warehouse_id TEXT PRIMARY KEY,
            name         TEXT NOT NULL,
            code         TEXT UNIQUE NOT NULL,
            address      TEXT,
            city         TEXT,
            state        TEXT,
            pincode      TEXT,
            latitude     REAL,
            longitude    REAL,
            is_primary   INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1,
            created_at   TEXT
        )
    """),

    # ─── Dealers (depends on territories, sales_persons) ───
    ("dealers", """
        CREATE TABLE IF NOT EXISTS dealers (
            dealer_id                  TEXT PRIMARY KEY,
            dealer_code                TEXT UNIQUE NOT NULL,
            name                       TEXT NOT NULL,
            trade_name                 TEXT,
            dealer_type                TEXT,
            category                   TEXT,
            contact_person             TEXT,
            contact_phone              TEXT,
            contact_email              TEXT,
            alternate_phone            TEXT,
            address_line1              TEXT,
            address_line2              TEXT,
            city                       TEXT,
            district                   TEXT,
            state                      TEXT,
            pincode                    TEXT,
            latitude                   REAL,
            longitude                  REAL,
            gstin                      TEXT,
            pan                        TEXT,
            credit_limit               REAL,
            credit_days                INTEGER,
            payment_mode               TEXT,
            territory_id               TEXT REFERENCES territories(territory_id),
            sales_person_id            TEXT REFERENCES sales_persons(sales_person_id),
            status                     TEXT DEFAULT 'ACTIVE',
            onboarding_date            TEXT,
            last_order_date            TEXT,
            last_visit_date            TEXT,
            commitment_fulfillment_rate REAL,
            avg_days_to_fulfill        INTEGER,
            created_at                 TEXT,
            updated_at                 TEXT
        )
    """),

    # ─── Inventory tables ───
    ("dealer_inventory", """
        CREATE TABLE IF NOT EXISTS dealer_inventory (
            dealer_inventory_id TEXT PRIMARY KEY,
            dealer_id           TEXT NOT NULL REFERENCES dealers(dealer_id),
            product_id          TEXT NOT NULL REFERENCES products(product_id),
            current_stock       INTEGER,
            reorder_point       INTEGER,
            max_stock           INTEGER,
            avg_daily_consumption REAL,
            days_of_stock       INTEGER,
            last_updated        TEXT
        )
    """),
    ("inventory", """
        CREATE TABLE IF NOT EXISTS inventory (
            inventory_id TEXT PRIMARY KEY,
            product_id   TEXT NOT NULL REFERENCES products(product_id),
            warehouse_id TEXT NOT NULL REFERENCES warehouses(warehouse_id),
            qty_on_hand  INTEGER,
            qty_reserved INTEGER,
            batch_number TEXT,
            expiry_date  TEXT,
            last_updated TEXT
        )
    """),
    ("incoming_stock", """
        CREATE TABLE IF NOT EXISTS incoming_stock (
            incoming_stock_id TEXT PRIMARY KEY,
            product_id        TEXT NOT NULL REFERENCES products(product_id),
            warehouse_id      TEXT NOT NULL REFERENCES warehouses(warehouse_id),
            quantity          INTEGER,
            expected_date     TEXT,
            source_type       TEXT,
            source_reference  TEXT,
            status            TEXT,
            actual_received_qty INTEGER,
            received_date     TEXT,
            created_at        TEXT,
            updated_at        TEXT
        )
    """),

    # ─── Production ───
    ("production_capacity", """
        CREATE TABLE IF NOT EXISTS production_capacity (
            capacity_id      TEXT PRIMARY KEY,
            product_id       TEXT NOT NULL REFERENCES products(product_id),
            daily_capacity   INTEGER,
            weekly_capacity  INTEGER,
            monthly_capacity INTEGER,
            effective_from   TEXT,
            effective_to     TEXT,
            notes            TEXT,
            created_at       TEXT
        )
    """),
    ("production_schedule", """
        CREATE TABLE IF NOT EXISTS production_schedule (
            schedule_id TEXT PRIMARY KEY,
            product_id  TEXT NOT NULL REFERENCES products(product_id),
            planned_date TEXT,
            planned_qty  INTEGER,
            actual_qty   INTEGER,
            status       TEXT,
            created_at   TEXT,
            updated_at   TEXT
        )
    """),

    # ─── Visits ───
    ("visits", """
        CREATE TABLE IF NOT EXISTS visits (
            visit_id           TEXT PRIMARY KEY,
            dealer_id          TEXT NOT NULL REFERENCES dealers(dealer_id),
            sales_person_id    TEXT NOT NULL REFERENCES sales_persons(sales_person_id),
            visit_date         TEXT,
            visit_type         TEXT,
            purpose            TEXT,
            check_in_time      TEXT,
            check_out_time     TEXT,
            duration_minutes   INTEGER,
            check_in_latitude  REAL,
            check_in_longitude REAL,
            outcome            TEXT,
            order_taken        INTEGER,
            order_id           TEXT,
            collection_amount  REAL,
            next_action        TEXT,
            next_visit_date    TEXT,
            follow_up_required INTEGER,
            raw_notes          TEXT,
            source             TEXT,
            created_at         TEXT,
            updated_at         TEXT
        )
    """),
    ("commitments", """
        CREATE TABLE IF NOT EXISTS commitments (
            commitment_id       TEXT PRIMARY KEY,
            visit_id            TEXT NOT NULL REFERENCES visits(visit_id),
            dealer_id           TEXT NOT NULL REFERENCES dealers(dealer_id),
            sales_person_id     TEXT NOT NULL REFERENCES sales_persons(sales_person_id),
            product_id          TEXT REFERENCES products(product_id),
            product_category_id TEXT,
            product_description TEXT,
            quantity_promised   INTEGER,
            unit_of_measure     TEXT,
            commitment_date     TEXT,
            expected_order_date TEXT,
            expected_delivery_date TEXT,
            status              TEXT DEFAULT 'PENDING',
            converted_order_id  TEXT,
            converted_quantity  INTEGER,
            conversion_date     TEXT,
            confidence_score    REAL,
            extraction_source   TEXT,
            is_consumed         INTEGER DEFAULT 0,
            consumed_by_order_id TEXT,
            notes               TEXT,
            created_at          TEXT,
            updated_at          TEXT
        )
    """),

    # ─── Orders ───
    ("orders", """
        CREATE TABLE IF NOT EXISTS orders (
            order_id               TEXT PRIMARY KEY,
            order_number           TEXT UNIQUE NOT NULL,
            dealer_id              TEXT NOT NULL REFERENCES dealers(dealer_id),
            sales_person_id        TEXT NOT NULL REFERENCES sales_persons(sales_person_id),
            order_date             TEXT,
            requested_delivery_date TEXT,
            promised_delivery_date TEXT,
            actual_delivery_date   TEXT,
            subtotal               REAL,
            discount_amount        REAL,
            discount_percent       REAL,
            tax_amount             REAL,
            total_amount           REAL,
            status                 TEXT DEFAULT 'DRAFT',
            payment_status         TEXT,
            source                 TEXT,
            commitment_id          TEXT,
            parent_order_id        TEXT,
            is_split               INTEGER DEFAULT 0,
            split_sequence         INTEGER,
            requires_approval      INTEGER DEFAULT 0,
            approved_by            TEXT,
            approved_at            TEXT,
            notes                  TEXT,
            created_at             TEXT,
            updated_at             TEXT
        )
    """),
    ("order_items", """
        CREATE TABLE IF NOT EXISTS order_items (
            order_item_id      TEXT PRIMARY KEY,
            order_id           TEXT NOT NULL REFERENCES orders(order_id),
            product_id         TEXT NOT NULL REFERENCES products(product_id),
            quantity_ordered   INTEGER,
            quantity_confirmed INTEGER,
            quantity_shipped   INTEGER,
            quantity_delivered  INTEGER,
            unit_price         REAL,
            discount_percent   REAL,
            discount_amount    REAL,
            tax_rate           REAL,
            tax_amount         REAL,
            line_total         REAL,
            original_quantity  TEXT,
            split_reason       TEXT,
            notes              TEXT,
            created_at         TEXT
        )
    """),
    ("order_splits", """
        CREATE TABLE IF NOT EXISTS order_splits (
            split_id               TEXT PRIMARY KEY,
            original_order_id      TEXT NOT NULL REFERENCES orders(order_id),
            split_order_id         TEXT NOT NULL,
            split_reason           TEXT,
            original_quantity      INTEGER,
            original_delivery_date TEXT,
            split_quantity         INTEGER,
            new_delivery_date      TEXT,
            discount_offered       REAL,
            discount_approved      INTEGER,
            discount_approved_by   TEXT,
            discount_approved_at   TEXT,
            alert_id               TEXT,
            created_by             TEXT,
            created_at             TEXT
        )
    """),

    # ─── Invoices & Payments ───
    ("invoices", """
        CREATE TABLE IF NOT EXISTS invoices (
            invoice_id      TEXT PRIMARY KEY,
            invoice_number  TEXT UNIQUE NOT NULL,
            order_id        TEXT NOT NULL REFERENCES orders(order_id),
            dealer_id       TEXT NOT NULL REFERENCES dealers(dealer_id),
            invoice_date    TEXT,
            due_date        TEXT,
            subtotal        REAL,
            discount_amount REAL,
            cgst_amount     REAL,
            sgst_amount     REAL,
            igst_amount     REAL,
            cess_amount     REAL,
            total_tax       REAL,
            total_amount    REAL,
            amount_paid     REAL,
            status          TEXT DEFAULT 'PENDING',
            created_at      TEXT,
            updated_at      TEXT
        )
    """),
    ("payments", """
        CREATE TABLE IF NOT EXISTS payments (
            payment_id      TEXT PRIMARY KEY,
            payment_number  TEXT UNIQUE NOT NULL,
            dealer_id       TEXT NOT NULL REFERENCES dealers(dealer_id),
            invoice_id      TEXT REFERENCES invoices(invoice_id),
            amount          REAL,
            payment_date    TEXT,
            payment_mode    TEXT,
            reference_number TEXT,
            bank_name       TEXT,
            collected_by    TEXT,
            visit_id        TEXT,
            status          TEXT DEFAULT 'CONFIRMED',
            notes           TEXT,
            created_at      TEXT,
            updated_at      TEXT
        )
    """),

    # ─── Issues ───
    ("issues", """
        CREATE TABLE IF NOT EXISTS issues (
            issue_id        TEXT PRIMARY KEY,
            dealer_id       TEXT NOT NULL REFERENCES dealers(dealer_id),
            sales_person_id TEXT REFERENCES sales_persons(sales_person_id),
            visit_id        TEXT REFERENCES visits(visit_id),
            issue_type      TEXT,
            priority        TEXT,
            subject         TEXT,
            description     TEXT,
            order_id        TEXT,
            product_id      TEXT,
            status          TEXT DEFAULT 'OPEN',
            assigned_to     TEXT,
            resolution      TEXT,
            resolved_at     TEXT,
            created_at      TEXT,
            updated_at      TEXT
        )
    """),

    # ─── Vehicles & Routes ───
    ("vehicles", """
        CREATE TABLE IF NOT EXISTS vehicles (
            vehicle_id         TEXT PRIMARY KEY,
            vehicle_number     TEXT UNIQUE NOT NULL,
            vehicle_type       TEXT,
            capacity_units     INTEGER,
            capacity_weight_kg INTEGER,
            capacity_volume_cbm REAL,
            warehouse_id       TEXT REFERENCES warehouses(warehouse_id),
            driver_name        TEXT,
            driver_phone       TEXT,
            status             TEXT DEFAULT 'AVAILABLE',
            is_active          INTEGER DEFAULT 1,
            created_at         TEXT
        )
    """),
    ("delivery_routes", """
        CREATE TABLE IF NOT EXISTS delivery_routes (
            route_id           TEXT PRIMARY KEY,
            route_date         TEXT,
            vehicle_id         TEXT NOT NULL REFERENCES vehicles(vehicle_id),
            total_capacity     INTEGER,
            utilized_capacity  INTEGER,
            status             TEXT,
            planned_start_time TEXT,
            actual_start_time  TEXT,
            planned_end_time   TEXT,
            actual_end_time    TEXT,
            total_distance_km  REAL,
            total_stops        INTEGER,
            created_at         TEXT,
            updated_at         TEXT
        )
    """),
    ("route_stops", """
        CREATE TABLE IF NOT EXISTS route_stops (
            stop_id             TEXT PRIMARY KEY,
            route_id            TEXT NOT NULL REFERENCES delivery_routes(route_id),
            dealer_id           TEXT NOT NULL REFERENCES dealers(dealer_id),
            order_id            TEXT REFERENCES orders(order_id),
            stop_sequence       INTEGER,
            stop_type           TEXT,
            quantity_to_deliver INTEGER,
            quantity_delivered  INTEGER,
            status              TEXT,
            planned_arrival     TEXT,
            actual_arrival      TEXT,
            departure_time      TEXT,
            is_drop_sale        INTEGER DEFAULT 0,
            drop_sale_source    TEXT,
            notes               TEXT,
            created_at          TEXT,
            updated_at          TEXT
        )
    """),

    # ─── Alerts ───
    ("alerts", """
        CREATE TABLE IF NOT EXISTS alerts (
            alert_id              TEXT PRIMARY KEY,
            alert_type            TEXT,
            priority              TEXT,
            assigned_to           TEXT REFERENCES sales_persons(sales_person_id),
            created_by            TEXT,
            entity_type           TEXT,
            entity_id             TEXT,
            title                 TEXT,
            message               TEXT,
            action_required       TEXT,
            context_data          TEXT,
            status                TEXT DEFAULT 'ACTIVE',
            response              TEXT,
            response_notes        TEXT,
            responded_at          TEXT,
            notification_sent     INTEGER DEFAULT 0,
            notification_channel  TEXT,
            notification_sent_at  TEXT,
            expires_at            TEXT,
            created_at            TEXT,
            updated_at            TEXT
        )
    """),

    # ─── Sales targets & health scores ───
    ("sales_targets", """
        CREATE TABLE IF NOT EXISTS sales_targets (
            target_id           TEXT PRIMARY KEY,
            sales_person_id     TEXT NOT NULL REFERENCES sales_persons(sales_person_id),
            territory_id        TEXT REFERENCES territories(territory_id),
            product_id          TEXT,
            product_category_id TEXT,
            period_type         TEXT,
            period_start        TEXT,
            period_end          TEXT,
            target_type         TEXT,
            target_value        REAL,
            achieved_value      REAL,
            achievement_percent REAL,
            notes               TEXT,
            created_at          TEXT,
            updated_at          TEXT
        )
    """),
    ("dealer_health_scores", """
        CREATE TABLE IF NOT EXISTS dealer_health_scores (
            score_id                       TEXT PRIMARY KEY,
            dealer_id                      TEXT NOT NULL REFERENCES dealers(dealer_id),
            calculated_date                TEXT,
            payment_score                  REAL,
            order_frequency_score          REAL,
            order_value_score              REAL,
            commitment_score               REAL,
            engagement_score               REAL,
            overall_score                  REAL,
            health_status                  TEXT,
            total_outstanding              REAL,
            days_since_last_order          INTEGER,
            days_since_last_visit          INTEGER,
            avg_order_value_30d            REAL,
            commitment_fulfillment_rate_90d REAL,
            requires_attention             INTEGER DEFAULT 0,
            attention_reason               TEXT,
            created_at                     TEXT
        )
    """),

    # ─── Weekly sales actuals (aggregation for ML) ───
    ("weekly_sales_actuals", """
        CREATE TABLE IF NOT EXISTS weekly_sales_actuals (
            week_id            TEXT PRIMARY KEY,
            week_start         TEXT,
            week_end           TEXT,
            week_number        INTEGER,
            year               INTEGER,
            month              INTEGER,
            product_id         TEXT NOT NULL REFERENCES products(product_id),
            product_code       TEXT,
            quantity_ordered   INTEGER,
            quantity_delivered  INTEGER,
            order_count        INTEGER,
            revenue            REAL,
            is_festival_week   INTEGER DEFAULT 0
        )
    """),
]

# ──────────── Indexes ────────────
INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_dealers_territory ON dealers(territory_id)",
    "CREATE INDEX IF NOT EXISTS idx_dealers_sales_person ON dealers(sales_person_id)",
    "CREATE INDEX IF NOT EXISTS idx_dealers_category ON dealers(category)",
    "CREATE INDEX IF NOT EXISTS idx_dealers_status ON dealers(status)",
    "CREATE INDEX IF NOT EXISTS idx_dealer_inventory_dealer ON dealer_inventory(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_dealer_inventory_product ON dealer_inventory(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_visits_dealer ON visits(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_visits_date ON visits(visit_date)",
    "CREATE INDEX IF NOT EXISTS idx_visits_sales_person ON visits(sales_person_id)",
    "CREATE INDEX IF NOT EXISTS idx_commitments_dealer ON commitments(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_commitments_status ON commitments(status)",
    "CREATE INDEX IF NOT EXISTS idx_commitments_expected ON commitments(expected_order_date)",
    "CREATE INDEX IF NOT EXISTS idx_orders_dealer ON orders(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_orders_date ON orders(order_date)",
    "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status)",
    "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_dealer ON invoices(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_order ON invoices(order_id)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status)",
    "CREATE INDEX IF NOT EXISTS idx_invoices_due ON invoices(due_date)",
    "CREATE INDEX IF NOT EXISTS idx_payments_dealer ON payments(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status)",
    "CREATE INDEX IF NOT EXISTS idx_alerts_assigned ON alerts(assigned_to)",
    "CREATE INDEX IF NOT EXISTS idx_health_dealer ON dealer_health_scores(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_health_status ON dealer_health_scores(health_status)",
    "CREATE INDEX IF NOT EXISTS idx_route_stops_route ON route_stops(route_id)",
    "CREATE INDEX IF NOT EXISTS idx_route_stops_dealer ON route_stops(dealer_id)",
    "CREATE INDEX IF NOT EXISTS idx_wsa_product ON weekly_sales_actuals(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_wsa_week ON weekly_sales_actuals(week_start)",
    "CREATE INDEX IF NOT EXISTS idx_sales_targets_person ON sales_targets(sales_person_id)",
    "CREATE INDEX IF NOT EXISTS idx_production_schedule_product ON production_schedule(product_id)",
    "CREATE INDEX IF NOT EXISTS idx_issues_dealer ON issues(dealer_id)",
]


def load_csv(conn: sqlite3.Connection, table_name: str):
    """Load a CSV file into an existing SQLite table."""
    csv_path = CSV_DIR / f"{table_name}.csv"
    if not csv_path.exists():
        print(f"  WARNING: {csv_path} not found, skipping")
        return 0

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames
        placeholders = ", ".join(["?"] * len(cols))
        col_names = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders})"

        rows = []
        for row in reader:
            # Convert empty strings to None for proper NULL handling
            values = [None if v == "" else v for v in row.values()]
            rows.append(values)

        conn.executemany(sql, rows)

    return len(rows)


def main():
    print(f"═══ Loading CSVs into SQLite ═══")
    print(f"  CSV dir : {CSV_DIR}")
    print(f"  DB path : {DB_PATH}")
    print()

    # Remove old DB if exists
    if DB_PATH.exists():
        try:
            DB_PATH.unlink()
            print("  Removed existing database")
        except PermissionError:
            print("  ERROR: Cannot delete existing DB — close any programs using it (DB Browser, IDE, etc.)")
            print(f"  Path: {DB_PATH}")
            return

    # Ensure data dir exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA journal_mode=WAL")
    # Defer FK enforcement until after all data is loaded
    conn.execute("PRAGMA foreign_keys=OFF")

    # Create tables
    print("── Creating tables ──")
    for table_name, ddl in SCHEMA:
        conn.execute(ddl)
        print(f"  ✓ {table_name}")
    conn.commit()

    # Load data
    print("\n── Loading data ──")
    total = 0
    for table_name, _ in SCHEMA:
        count = load_csv(conn, table_name)
        total += count
        print(f"  {table_name:35s} → {count:>6d} rows")
    conn.commit()

    # Create indexes
    print("\n── Creating indexes ──")
    for idx_sql in INDEXES:
        conn.execute(idx_sql)
    conn.commit()
    print(f"  ✓ {len(INDEXES)} indexes created")

    # Quick verification
    print("\n── Verification ──")
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  Tables in DB: {len(tables)}")

    # FK check
    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        print(f"  ⚠ FK violations: {len(violations)}")
        for v in violations[:5]:
            print(f"    {v}")
    else:
        print(f"  ✓ No FK violations")

    # File size
    conn.close()
    size_mb = DB_PATH.stat().st_size / (1024 * 1024)
    print(f"\n  DB size: {size_mb:.2f} MB")
    print(f"  Total rows loaded: {total}")
    print(f"\n═══ DONE ═══")


if __name__ == "__main__":
    main()
