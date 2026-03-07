---
inclusion: auto
---

# Database Schema Reference

## Connection Details

**PostgreSQL RDS Instance**:
- Host: `scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com`
- Port: 5432
- Database: `supplychain`
- User: `scm_admin`
- Password: `scm-copilot`
- SSL Mode: `require`

## Key Tables & Relationships

### Core Entities

**dealers** - Retail outlets purchasing products
- Primary Key: `dealer_id` (UUID)
- Human-readable: `dealer_code` (e.g., "DLR-001")
- Location: `latitude`, `longitude` (for map display)
- Health: Computed from `dealer_health_scores` table

**sales_persons** - Sales representatives managing territories
- Primary Key: `sales_person_id` (UUID)
- Human-readable: `sales_person_code` (e.g., "SP-001")
- Contact: `phone`, `telegram_username`
- Linked to territories via `territory_assignments`

**products** - SKUs available for sale
- Primary Key: `product_id` (UUID)
- Human-readable: `product_code` (e.g., "CLN-1KG")
- Hierarchy: `category_id` → `product_categories`
- Tax: `hsn_code_id` → `hsn_codes`

### Transactional Tables

**visits** - Sales rep visits to dealers
- Links: `sales_person_id`, `dealer_id`
- Content: `raw_notes` (not `notes`), `visit_date`
- Status: `status` (COMPLETED, SCHEDULED, CANCELLED)

**commitments** - Promises made during visits
- Links: `visit_id`, `dealer_id`
- Details: `commitment_date`, `expected_order_date`, `expected_amount`
- Status: `status` (PENDING, FULFILLED, EXPIRED)

**orders** - Purchase orders from dealers
- Links: `dealer_id`, `sales_person_id`
- Amounts: `total_amount`, `status`
- Items: Join to `order_items` for product-level details

**order_items** - Line items in orders
- Links: `order_id`, `product_id`
- Quantities: `quantity`, `unit_price`, `total_price`

**invoices** - Billing documents
- Links: `order_id`, `dealer_id`
- Amounts: `invoice_amount`, `due_date`
- Status: `status` (DRAFT, SENT, PAID, OVERDUE)

**payments** - Payment transactions
- Links: `invoice_id`, `dealer_id`
- Amounts: `amount_paid`, `payment_date`
- Method: `payment_method` (CASH, CHEQUE, ONLINE, UPI)

### Analytics Tables

**dealer_health_scores** - Time-series health metrics
- Links: `dealer_id`
- Metrics: `payment_score`, `order_frequency_score`, `total_score`
- Time: `score_date` (one row per dealer per day)
- Health: `health_status` (healthy, at-risk, critical, unknown)

**sales_targets** - Monthly targets per sales rep
- Links: `sales_person_id`
- Target: `target_value`, `target_month`
- Achievement: Compare to actual orders in that month

**weekly_sales_actuals** - Historical sales for forecasting
- Links: `product_id`
- Metrics: `week_start_date`, `units_sold`
- Used by: `scripts/train_forecast_model.py`

**alerts** - System-generated notifications
- Polymorphic: `entity_type` + `entity_id` (can link to dealers, orders, etc.)
- Content: `message`, `priority` (not `severity`)
- Status: `status` (ACTIVE, RESOLVED, DISMISSED)

### Inventory & Production

**inventory** - Warehouse stock levels
- Links: `warehouse_id`, `product_id`
- Levels: `quantity_available`, `reorder_level`

**production_schedule** - Manufacturing batches
- Links: `product_id`
- Batch: `batch_number`, `planned_quantity`, `actual_quantity`
- Dates: `scheduled_date`, `completion_date`

**incoming_stock** - Expected deliveries
- Links: `warehouse_id`, `product_id`
- Details: `expected_quantity`, `expected_date`, `status`

## Important Schema Notes

### Date Handling
- All dates stored as TEXT in `YYYY-MM-DD` format
- Use `::date` cast for arithmetic: `(date1::date - date2::date)`
- Current date: `CURRENT_DATE` (not `date('now')`)

### Boolean Columns
- PostgreSQL native BOOLEAN type
- Values: `TRUE`, `FALSE`, `NULL`
- Migrated from SQLite 0/1 with explicit coercion

### UUID Primary Keys
- All entity tables use UUID primary keys
- Human-readable codes in separate columns (`dealer_code`, `product_code`, etc.)
- Use `gen_random_uuid()` for new records

### Common Query Patterns

**Latest health score per dealer**:
```sql
SELECT DISTINCT ON (dealer_id) *
FROM dealer_health_scores
ORDER BY dealer_id, score_date DESC
```

**Month-filtered metrics with trends**:
```sql
-- Current month
WHERE order_date >= '2026-02-01' AND order_date < '2026-03-01'

-- Previous month (for trend calculation)
WHERE order_date >= '2026-01-01' AND order_date < '2026-02-01'
```

**Pre-aggregated multi-dimensional joins**:
```sql
WITH
rep_orders AS (SELECT sales_person_id, SUM(total_amount) as total FROM orders GROUP BY sales_person_id),
rep_visits AS (SELECT sales_person_id, COUNT(*) as count FROM visits GROUP BY sales_person_id)
SELECT sp.*, ro.total, rv.count
FROM sales_persons sp
LEFT JOIN rep_orders ro USING (sales_person_id)
LEFT JOIN rep_visits rv USING (sales_person_id)
```

## Data Characteristics

- **Time Range**: 2025-03-28 to 2026-03-05 (shifted for demo)
- **Geography**: Delhi NCR only
- **Total Records**: ~8,700 across 30+ tables
- **Dealers**: 45 active dealers
- **Sales Reps**: 5 representatives
- **Products**: 3 SKUs (500g, 1kg, 2kg detergent)

## Schema Migration Notes

When migrating from SQLite to PostgreSQL:
- Replace `?` placeholders with `%s`
- Replace `GROUP_CONCAT` with `STRING_AGG`
- Replace `julianday()` with date arithmetic
- Disable FK constraints during bulk load: `SET session_replication_role = 'replica'`
- Explicitly cast boolean columns from 0/1

Full schema DDL: `scripts/create_pg_schema.sql`
