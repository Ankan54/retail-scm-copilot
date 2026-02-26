-- SupplyChain Copilot — PostgreSQL Schema
-- Converted from SQLite. Key changes:
--   TEXT → VARCHAR(36) for UUIDs, TEXT for long strings
--   REAL → NUMERIC(12,2) for money, REAL for coords
--   INTEGER(0/1) → BOOLEAN where appropriate
--   date('now') → CURRENT_DATE
--   CREATE INDEX IF NOT EXISTS → supported in PG 9.5+

-- Drop and recreate (careful: order matters for FK constraints)
-- Run with: psql -h <host> -U scm_admin -d supplychain -f create_pg_schema.sql

-- ─────────────────────────────────────────────────────────────────────────────
-- Reference / Master Tables
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS territories (
    territory_id        VARCHAR(36) PRIMARY KEY,
    name                TEXT NOT NULL,
    region              TEXT,
    state               TEXT,
    parent_territory_id VARCHAR(36),
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TEXT,
    updated_at          TEXT
);

CREATE TABLE IF NOT EXISTS product_categories (
    category_id        VARCHAR(36) PRIMARY KEY,
    name               TEXT NOT NULL,
    parent_category_id VARCHAR(36),
    description        TEXT,
    is_active          BOOLEAN DEFAULT TRUE,
    created_at         TEXT
);

CREATE TABLE IF NOT EXISTS hsn_codes (
    hsn_code       VARCHAR(20) PRIMARY KEY,
    description    TEXT,
    gst_rate       NUMERIC(5,2),
    cgst_rate      NUMERIC(5,2),
    sgst_rate      NUMERIC(5,2),
    igst_rate      NUMERIC(5,2),
    cess_rate      NUMERIC(5,2),
    effective_from TEXT,
    effective_to   TEXT,
    created_at     TEXT
);

CREATE TABLE IF NOT EXISTS system_settings (
    setting_key   TEXT PRIMARY KEY,
    setting_value TEXT,
    setting_type  TEXT,
    description   TEXT
);

CREATE TABLE IF NOT EXISTS consumption_config (
    config_id              VARCHAR(36) PRIMARY KEY,
    product_id             VARCHAR(36),
    dealer_id              VARCHAR(36),
    backward_days          INTEGER,
    forward_days           INTEGER,
    direction_priority     TEXT,
    quantity_tolerance_pct INTEGER,
    expire_after_days      INTEGER,
    effective_from         TEXT,
    effective_to           TEXT,
    created_at             TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sales Persons (self-referencing)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_persons (
    sales_person_id  VARCHAR(36) PRIMARY KEY,
    employee_code    TEXT UNIQUE NOT NULL,
    name             TEXT NOT NULL,
    email            TEXT,
    phone            TEXT,
    role             TEXT,
    manager_id       VARCHAR(36) REFERENCES sales_persons(sales_person_id),
    telegram_user_id TEXT,
    telegram_chat_id TEXT,
    is_active        BOOLEAN DEFAULT TRUE,
    date_of_joining  TEXT,
    created_at       TEXT,
    updated_at       TEXT
);

CREATE TABLE IF NOT EXISTS territory_assignments (
    assignment_id   VARCHAR(36) PRIMARY KEY,
    sales_person_id VARCHAR(36) NOT NULL REFERENCES sales_persons(sales_person_id),
    territory_id    VARCHAR(36) NOT NULL REFERENCES territories(territory_id),
    is_primary      BOOLEAN DEFAULT TRUE,
    assigned_date   TEXT,
    end_date        TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Products & Warehouses
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS products (
    product_id        VARCHAR(36) PRIMARY KEY,
    product_code      TEXT UNIQUE NOT NULL,
    name              TEXT NOT NULL,
    short_name        TEXT,
    description       TEXT,
    category_id       VARCHAR(36) REFERENCES product_categories(category_id),
    brand             TEXT,
    hsn_code          VARCHAR(20) REFERENCES hsn_codes(hsn_code),
    mrp               NUMERIC(12,2),
    unit_price        NUMERIC(12,2),
    dealer_price      NUMERIC(12,2),
    distributor_price NUMERIC(12,2),
    unit_of_measure   TEXT,
    units_per_case    INTEGER,
    min_order_qty     INTEGER,
    reorder_level     INTEGER,
    safety_stock      INTEGER,
    lead_time_days    INTEGER,
    is_manufactured   BOOLEAN,
    status            TEXT DEFAULT 'ACTIVE',
    launch_date       TEXT,
    discontinue_date  TEXT,
    created_at        TEXT,
    updated_at        TEXT
);

CREATE TABLE IF NOT EXISTS warehouses (
    warehouse_id VARCHAR(36) PRIMARY KEY,
    name         TEXT NOT NULL,
    code         TEXT UNIQUE NOT NULL,
    address      TEXT,
    city         TEXT,
    state        TEXT,
    pincode      TEXT,
    latitude     REAL,
    longitude    REAL,
    is_primary   BOOLEAN DEFAULT FALSE,
    is_active    BOOLEAN DEFAULT TRUE,
    created_at   TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Dealers
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dealers (
    dealer_id                  VARCHAR(36) PRIMARY KEY,
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
    credit_limit               NUMERIC(12,2),
    credit_days                INTEGER,
    payment_mode               TEXT,
    territory_id               VARCHAR(36) REFERENCES territories(territory_id),
    sales_person_id            VARCHAR(36) REFERENCES sales_persons(sales_person_id),
    status                     TEXT DEFAULT 'ACTIVE',
    onboarding_date            TEXT,
    last_order_date            TEXT,
    last_visit_date            TEXT,
    commitment_fulfillment_rate NUMERIC(5,2),
    avg_days_to_fulfill        INTEGER,
    created_at                 TEXT,
    updated_at                 TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Inventory
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS dealer_inventory (
    dealer_inventory_id VARCHAR(36) PRIMARY KEY,
    dealer_id           VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    product_id          VARCHAR(36) NOT NULL REFERENCES products(product_id),
    current_stock       INTEGER,
    reorder_point       INTEGER,
    max_stock           INTEGER,
    avg_daily_consumption NUMERIC(10,2),
    days_of_stock       INTEGER,
    last_updated        TEXT
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id VARCHAR(36) PRIMARY KEY,
    product_id   VARCHAR(36) NOT NULL REFERENCES products(product_id),
    warehouse_id VARCHAR(36) NOT NULL REFERENCES warehouses(warehouse_id),
    qty_on_hand  INTEGER,
    qty_reserved INTEGER,
    batch_number TEXT,
    expiry_date  TEXT,
    last_updated TEXT
);

CREATE TABLE IF NOT EXISTS incoming_stock (
    incoming_stock_id   VARCHAR(36) PRIMARY KEY,
    product_id          VARCHAR(36) NOT NULL REFERENCES products(product_id),
    warehouse_id        VARCHAR(36) NOT NULL REFERENCES warehouses(warehouse_id),
    quantity            INTEGER,
    expected_date       TEXT,
    source_type         TEXT,
    source_reference    TEXT,
    status              TEXT,
    actual_received_qty INTEGER,
    received_date       TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Production
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS production_capacity (
    capacity_id      VARCHAR(36) PRIMARY KEY,
    product_id       VARCHAR(36) NOT NULL REFERENCES products(product_id),
    daily_capacity   INTEGER,
    weekly_capacity  INTEGER,
    monthly_capacity INTEGER,
    effective_from   TEXT,
    effective_to     TEXT,
    notes            TEXT,
    created_at       TEXT
);

CREATE TABLE IF NOT EXISTS production_schedule (
    schedule_id  VARCHAR(36) PRIMARY KEY,
    product_id   VARCHAR(36) NOT NULL REFERENCES products(product_id),
    planned_date TEXT,
    planned_qty  INTEGER,
    actual_qty   INTEGER,
    status       TEXT,
    created_at   TEXT,
    updated_at   TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Visits & Commitments
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS visits (
    visit_id           VARCHAR(36) PRIMARY KEY,
    dealer_id          VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    sales_person_id    VARCHAR(36) NOT NULL REFERENCES sales_persons(sales_person_id),
    visit_date         TEXT,
    visit_type         TEXT,
    purpose            TEXT,
    check_in_time      TEXT,
    check_out_time     TEXT,
    duration_minutes   INTEGER,
    check_in_latitude  REAL,
    check_in_longitude REAL,
    outcome            TEXT,
    order_taken        BOOLEAN DEFAULT FALSE,
    order_id           VARCHAR(36),
    collection_amount  NUMERIC(12,2),
    next_action        TEXT,
    next_visit_date    TEXT,
    follow_up_required BOOLEAN DEFAULT FALSE,
    raw_notes          TEXT,
    source             TEXT,
    created_at         TEXT,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS commitments (
    commitment_id          VARCHAR(36) PRIMARY KEY,
    visit_id               VARCHAR(36) NOT NULL REFERENCES visits(visit_id),
    dealer_id              VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    sales_person_id        VARCHAR(36) NOT NULL REFERENCES sales_persons(sales_person_id),
    product_id             VARCHAR(36) REFERENCES products(product_id),
    product_category_id    TEXT,
    product_description    TEXT,
    quantity_promised       INTEGER,
    unit_of_measure        TEXT,
    commitment_date        TEXT,
    expected_order_date    TEXT,
    expected_delivery_date TEXT,
    status                 TEXT DEFAULT 'PENDING',
    converted_order_id     VARCHAR(36),
    converted_quantity     INTEGER,
    conversion_date        TEXT,
    confidence_score       NUMERIC(4,2),
    extraction_source      TEXT,
    is_consumed            BOOLEAN DEFAULT FALSE,
    consumed_by_order_id   VARCHAR(36),
    notes                  TEXT,
    created_at             TEXT,
    updated_at             TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Orders
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS orders (
    order_id                VARCHAR(36) PRIMARY KEY,
    order_number            TEXT UNIQUE NOT NULL,
    dealer_id               VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    sales_person_id         VARCHAR(36) NOT NULL REFERENCES sales_persons(sales_person_id),
    order_date              TEXT,
    requested_delivery_date TEXT,
    promised_delivery_date  TEXT,
    actual_delivery_date    TEXT,
    subtotal                NUMERIC(12,2),
    discount_amount         NUMERIC(12,2),
    discount_percent        NUMERIC(5,2),
    tax_amount              NUMERIC(12,2),
    total_amount            NUMERIC(12,2),
    status                  TEXT DEFAULT 'DRAFT',
    payment_status          TEXT,
    source                  TEXT,
    commitment_id           VARCHAR(36),
    parent_order_id         VARCHAR(36),
    is_split                BOOLEAN DEFAULT FALSE,
    split_sequence          INTEGER,
    requires_approval       BOOLEAN DEFAULT FALSE,
    approved_by             VARCHAR(36),
    approved_at             TEXT,
    notes                   TEXT,
    created_at              TEXT,
    updated_at              TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id      VARCHAR(36) PRIMARY KEY,
    order_id           VARCHAR(36) NOT NULL REFERENCES orders(order_id),
    product_id         VARCHAR(36) NOT NULL REFERENCES products(product_id),
    quantity_ordered   INTEGER,
    quantity_confirmed INTEGER,
    quantity_shipped   INTEGER,
    quantity_delivered INTEGER,
    unit_price         NUMERIC(12,2),
    discount_percent   NUMERIC(5,2),
    discount_amount    NUMERIC(12,2),
    tax_rate           NUMERIC(5,2),
    tax_amount         NUMERIC(12,2),
    line_total         NUMERIC(12,2),
    original_quantity  TEXT,
    split_reason       TEXT,
    notes              TEXT,
    created_at         TEXT
);

CREATE TABLE IF NOT EXISTS order_splits (
    split_id               VARCHAR(36) PRIMARY KEY,
    original_order_id      VARCHAR(36) NOT NULL REFERENCES orders(order_id),
    split_order_id         VARCHAR(36) NOT NULL,
    split_reason           TEXT,
    original_quantity      INTEGER,
    original_delivery_date TEXT,
    split_quantity         INTEGER,
    new_delivery_date      TEXT,
    discount_offered       NUMERIC(5,2),
    discount_approved      BOOLEAN,
    discount_approved_by   VARCHAR(36),
    discount_approved_at   TEXT,
    alert_id               VARCHAR(36),
    created_by             VARCHAR(36),
    created_at             TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Invoices & Payments
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id      VARCHAR(36) PRIMARY KEY,
    invoice_number  TEXT UNIQUE NOT NULL,
    order_id        VARCHAR(36) NOT NULL REFERENCES orders(order_id),
    dealer_id       VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    invoice_date    TEXT,
    due_date        TEXT,
    subtotal        NUMERIC(12,2),
    discount_amount NUMERIC(12,2),
    cgst_amount     NUMERIC(12,2),
    sgst_amount     NUMERIC(12,2),
    igst_amount     NUMERIC(12,2),
    cess_amount     NUMERIC(12,2),
    total_tax       NUMERIC(12,2),
    total_amount    NUMERIC(12,2),
    amount_paid     NUMERIC(12,2),
    status          TEXT DEFAULT 'PENDING',
    created_at      TEXT,
    updated_at      TEXT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id       VARCHAR(36) PRIMARY KEY,
    payment_number   TEXT UNIQUE NOT NULL,
    dealer_id        VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    invoice_id       VARCHAR(36) REFERENCES invoices(invoice_id),
    amount           NUMERIC(12,2),
    payment_date     TEXT,
    payment_mode     TEXT,
    reference_number TEXT,
    bank_name        TEXT,
    collected_by     VARCHAR(36),
    visit_id         VARCHAR(36),
    status           TEXT DEFAULT 'CONFIRMED',
    notes            TEXT,
    created_at       TEXT,
    updated_at       TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Issues
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS issues (
    issue_id        VARCHAR(36) PRIMARY KEY,
    dealer_id       VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    sales_person_id VARCHAR(36) REFERENCES sales_persons(sales_person_id),
    visit_id        VARCHAR(36) REFERENCES visits(visit_id),
    issue_type      TEXT,
    priority        TEXT,
    subject         TEXT,
    description     TEXT,
    order_id        VARCHAR(36),
    product_id      VARCHAR(36),
    status          TEXT DEFAULT 'OPEN',
    assigned_to     VARCHAR(36),
    resolution      TEXT,
    resolved_at     TEXT,
    created_at      TEXT,
    updated_at      TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Vehicles & Routes
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS vehicles (
    vehicle_id          VARCHAR(36) PRIMARY KEY,
    vehicle_number      TEXT UNIQUE NOT NULL,
    vehicle_type        TEXT,
    capacity_units      INTEGER,
    capacity_weight_kg  INTEGER,
    capacity_volume_cbm NUMERIC(10,2),
    warehouse_id        VARCHAR(36) REFERENCES warehouses(warehouse_id),
    driver_name         TEXT,
    driver_phone        TEXT,
    status              TEXT DEFAULT 'AVAILABLE',
    is_active           BOOLEAN DEFAULT TRUE,
    created_at          TEXT
);

CREATE TABLE IF NOT EXISTS delivery_routes (
    route_id           VARCHAR(36) PRIMARY KEY,
    route_date         TEXT,
    vehicle_id         VARCHAR(36) NOT NULL REFERENCES vehicles(vehicle_id),
    total_capacity     INTEGER,
    utilized_capacity  INTEGER,
    status             TEXT,
    planned_start_time TEXT,
    actual_start_time  TEXT,
    planned_end_time   TEXT,
    actual_end_time    TEXT,
    total_distance_km  NUMERIC(10,2),
    total_stops        INTEGER,
    created_at         TEXT,
    updated_at         TEXT
);

CREATE TABLE IF NOT EXISTS route_stops (
    stop_id             VARCHAR(36) PRIMARY KEY,
    route_id            VARCHAR(36) NOT NULL REFERENCES delivery_routes(route_id),
    dealer_id           VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    order_id            VARCHAR(36) REFERENCES orders(order_id),
    stop_sequence       INTEGER,
    stop_type           TEXT,
    quantity_to_deliver INTEGER,
    quantity_delivered  INTEGER,
    status              TEXT,
    planned_arrival     TEXT,
    actual_arrival      TEXT,
    departure_time      TEXT,
    is_drop_sale        BOOLEAN DEFAULT FALSE,
    drop_sale_source    TEXT,
    notes               TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Alerts
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS alerts (
    alert_id             VARCHAR(36) PRIMARY KEY,
    alert_type           TEXT,
    priority             TEXT,
    assigned_to          VARCHAR(36) REFERENCES sales_persons(sales_person_id),
    created_by           VARCHAR(36),
    entity_type          TEXT,
    entity_id            VARCHAR(36),
    title                TEXT,
    message              TEXT,
    action_required      TEXT,
    context_data         TEXT,
    status               TEXT DEFAULT 'ACTIVE',
    response             TEXT,
    response_notes       TEXT,
    responded_at         TEXT,
    notification_sent    BOOLEAN DEFAULT FALSE,
    notification_channel TEXT,
    notification_sent_at TEXT,
    expires_at           TEXT,
    created_at           TEXT,
    updated_at           TEXT
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sales Targets & Health Scores
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sales_targets (
    target_id           VARCHAR(36) PRIMARY KEY,
    sales_person_id     VARCHAR(36) NOT NULL REFERENCES sales_persons(sales_person_id),
    territory_id        VARCHAR(36) REFERENCES territories(territory_id),
    product_id          VARCHAR(36),
    product_category_id VARCHAR(36),
    period_type         TEXT,
    period_start        TEXT,
    period_end          TEXT,
    target_type         TEXT,
    target_value        NUMERIC(14,2),
    achieved_value      NUMERIC(14,2),
    achievement_percent NUMERIC(6,2),
    notes               TEXT,
    created_at          TEXT,
    updated_at          TEXT
);

CREATE TABLE IF NOT EXISTS dealer_health_scores (
    score_id                        VARCHAR(36) PRIMARY KEY,
    dealer_id                       VARCHAR(36) NOT NULL REFERENCES dealers(dealer_id),
    calculated_date                 TEXT,
    payment_score                   NUMERIC(5,2),
    order_frequency_score           NUMERIC(5,2),
    order_value_score               NUMERIC(5,2),
    commitment_score                NUMERIC(5,2),
    engagement_score                NUMERIC(5,2),
    overall_score                   NUMERIC(5,2),
    health_status                   TEXT,
    total_outstanding               NUMERIC(12,2),
    days_since_last_order           INTEGER,
    days_since_last_visit           INTEGER,
    avg_order_value_30d             NUMERIC(12,2),
    commitment_fulfillment_rate_90d NUMERIC(5,2),
    requires_attention              BOOLEAN DEFAULT FALSE,
    attention_reason                TEXT,
    created_at                      TEXT
);

CREATE TABLE IF NOT EXISTS weekly_sales_actuals (
    week_id            TEXT PRIMARY KEY,
    week_start         TEXT,
    week_end           TEXT,
    week_number        INTEGER,
    year               INTEGER,
    month              INTEGER,
    product_id         VARCHAR(36) NOT NULL REFERENCES products(product_id),
    product_code       TEXT,
    quantity_ordered   INTEGER,
    quantity_delivered INTEGER,
    order_count        INTEGER,
    revenue            NUMERIC(14,2),
    is_festival_week   BOOLEAN DEFAULT FALSE
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Sessions (replaces DynamoDB supplychain-sessions)
-- ─────────────────────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    session_id      VARCHAR(36) PRIMARY KEY,
    telegram_chat_id TEXT,
    sales_person_id VARCHAR(36),
    agent_session_id TEXT,
    context         TEXT,            -- JSON blob
    last_message    TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW() + INTERVAL '24 hours'
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Indexes
-- ─────────────────────────────────────────────────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_dealers_territory    ON dealers(territory_id);
CREATE INDEX IF NOT EXISTS idx_dealers_sales_person ON dealers(sales_person_id);
CREATE INDEX IF NOT EXISTS idx_dealers_category     ON dealers(category);
CREATE INDEX IF NOT EXISTS idx_dealers_status       ON dealers(status);
CREATE INDEX IF NOT EXISTS idx_dealer_inv_dealer    ON dealer_inventory(dealer_id);
CREATE INDEX IF NOT EXISTS idx_dealer_inv_product   ON dealer_inventory(product_id);
CREATE INDEX IF NOT EXISTS idx_visits_dealer        ON visits(dealer_id);
CREATE INDEX IF NOT EXISTS idx_visits_date          ON visits(visit_date);
CREATE INDEX IF NOT EXISTS idx_visits_sp            ON visits(sales_person_id);
CREATE INDEX IF NOT EXISTS idx_commitments_dealer   ON commitments(dealer_id);
CREATE INDEX IF NOT EXISTS idx_commitments_status   ON commitments(status);
CREATE INDEX IF NOT EXISTS idx_commitments_expected ON commitments(expected_order_date);
CREATE INDEX IF NOT EXISTS idx_orders_dealer        ON orders(dealer_id);
CREATE INDEX IF NOT EXISTS idx_orders_date          ON orders(order_date);
CREATE INDEX IF NOT EXISTS idx_orders_status        ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order    ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_product  ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_invoices_dealer      ON invoices(dealer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_order       ON invoices(order_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status      ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due         ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_payments_dealer      ON payments(dealer_id);
CREATE INDEX IF NOT EXISTS idx_payments_invoice     ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status        ON alerts(status);
CREATE INDEX IF NOT EXISTS idx_alerts_assigned      ON alerts(assigned_to);
CREATE INDEX IF NOT EXISTS idx_health_dealer        ON dealer_health_scores(dealer_id);
CREATE INDEX IF NOT EXISTS idx_health_status        ON dealer_health_scores(health_status);
CREATE INDEX IF NOT EXISTS idx_route_stops_route    ON route_stops(route_id);
CREATE INDEX IF NOT EXISTS idx_route_stops_dealer   ON route_stops(dealer_id);
CREATE INDEX IF NOT EXISTS idx_wsa_product          ON weekly_sales_actuals(product_id);
CREATE INDEX IF NOT EXISTS idx_wsa_week             ON weekly_sales_actuals(week_start);
CREATE INDEX IF NOT EXISTS idx_sales_targets_sp     ON sales_targets(sales_person_id);
CREATE INDEX IF NOT EXISTS idx_production_sched     ON production_schedule(product_id);
CREATE INDEX IF NOT EXISTS idx_issues_dealer        ON issues(dealer_id);
CREATE INDEX IF NOT EXISTS idx_sessions_chat        ON sessions(telegram_chat_id);
CREATE INDEX IF NOT EXISTS idx_sessions_sp          ON sessions(sales_person_id);
CREATE INDEX IF NOT EXISTS idx_sessions_expires     ON sessions(expires_at);
