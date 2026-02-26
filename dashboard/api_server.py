"""
Local API server for SupplyChain Copilot Dashboard
Queries PostgreSQL directly and serves dashboard data on port 8000.
Vite dev server proxies /api/* -> http://localhost:8000/api/*

Run: ../.venv/Scripts/python api_server.py
"""
import json
import sys
import os
from datetime import datetime

# Add project root to path for .env loading
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import psycopg2
    import psycopg2.extras
    import uvicorn
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "psycopg2-binary"], check=True)
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import psycopg2
    import psycopg2.extras
    import uvicorn

app = FastAPI(title="SupplyChain Copilot API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com"),
    "port": int(os.getenv("DB_PORT", 5432)),
    "dbname": os.getenv("DB_NAME", "supplychain"),
    "user": os.getenv("DB_USER", "scm_admin"),
    "password": os.getenv("DB_PASSWORD", "scm-copilot"),
    "sslmode": "require",
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)

def fmt_r(rows):
    """Convert RealDictRow list to plain dicts"""
    return [dict(r) for r in rows]

# ─── /api/metrics ─────────────────────────────────────────────────────────────
@app.get("/api/metrics")
def get_metrics():
    conn = get_conn()
    cur = conn.cursor()

    # Total revenue & collections this month
    cur.execute("""
        SELECT COALESCE(SUM(total_amount), 0) AS revenue
        FROM orders
        WHERE order_date >= (CURRENT_DATE - INTERVAL '30 days')::text
    """)
    revenue = float(cur.fetchone()["revenue"])

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0) AS collections
        FROM payments
        WHERE payment_date >= (CURRENT_DATE - INTERVAL '30 days')::text
    """)
    collections = float(cur.fetchone()["collections"])

    # Active dealers
    cur.execute("SELECT COUNT(*) AS cnt FROM dealers WHERE status = 'ACTIVE'")
    active_dealers = cur.fetchone()["cnt"]

    # At-risk dealers (latest health score per dealer)
    cur.execute("""
        SELECT COUNT(*) AS cnt FROM (
            SELECT DISTINCT ON (dealer_id) health_status
            FROM dealer_health_scores ORDER BY dealer_id, calculated_date DESC
        ) s WHERE health_status IN ('AT_RISK', 'CRITICAL')
    """)
    at_risk = cur.fetchone()["cnt"]

    # Dealers visited in last 30 days
    cur.execute("""
        SELECT COUNT(DISTINCT dealer_id) AS cnt FROM visits
        WHERE visit_date >= (CURRENT_DATE - INTERVAL '30 days')::text
    """)
    visited = cur.fetchone()["cnt"]

    # Commitment pipeline value = quantity_promised * dealer_price joined to products
    cur.execute("""
        SELECT
            COUNT(*) AS total_count,
            COALESCE(SUM(c.quantity_promised * p.dealer_price), 0) AS total_value
        FROM commitments c
        LEFT JOIN products p ON c.product_id = p.product_id
        WHERE c.status NOT IN ('CANCELLED', 'EXPIRED')
    """)
    r = cur.fetchone()
    pipeline_count = r["total_count"]
    pipeline_value = float(r["total_value"])

    # Monthly target (sum for current month)
    cur.execute("""
        SELECT COALESCE(SUM(target_amount), 0) AS target
        FROM sales_targets
        WHERE TO_CHAR(CURRENT_DATE, 'YYYY-MM') = ANY(
            SELECT TO_CHAR(period_start::date, 'YYYY-MM') FROM sales_targets
        )
    """)
    try:
        target = float(cur.fetchone()["target"])
    except Exception:
        target = 4200000  # fallback

    conn.close()
    return {
        "revenue": revenue,
        "collections": collections,
        "active_dealers": active_dealers,
        "at_risk": at_risk,
        "visited_30d": visited,
        "pipeline_count": pipeline_count,
        "pipeline_value": pipeline_value,
        "monthly_target": target,
        "target_pct": round(collections / target * 100, 1) if target else 0,
    }


# ─── /api/dealers ─────────────────────────────────────────────────────────────
@app.get("/api/dealers")
def get_dealers():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            d.dealer_id AS id,
            d.name,
            d.city,
            d.latitude AS lat,
            d.longitude AS lng,
            d.category,
            COALESCE(dhs.health_status, 'UNKNOWN') AS health,
            COALESCE(SUM(o.total_amount), 0) AS revenue,
            COALESCE(SUM(p.amount), 0) AS collections,
            COALESCE(
                (SELECT SUM(o2.total_amount) FROM orders o2
                 WHERE o2.dealer_id = d.dealer_id AND o2.payment_status = 'PENDING'), 0
            ) AS outstanding,
            (SELECT MAX(v.visit_date) FROM visits v WHERE v.dealer_id = d.dealer_id) AS last_visit,
            (SELECT COUNT(*) FROM commitments c WHERE c.dealer_id = d.dealer_id AND c.status = 'PENDING') AS pending_commitments,
            sp.name AS sales_rep
        FROM dealers d
        LEFT JOIN (
            SELECT DISTINCT ON (dealer_id) dealer_id, health_status
            FROM dealer_health_scores ORDER BY dealer_id, calculated_date DESC
        ) dhs ON d.dealer_id = dhs.dealer_id
        LEFT JOIN orders o ON o.dealer_id = d.dealer_id
            AND o.order_date >= (CURRENT_DATE - INTERVAL '30 days')::text
        LEFT JOIN payments p ON p.dealer_id = d.dealer_id
            AND p.payment_date >= (CURRENT_DATE - INTERVAL '30 days')::text
        LEFT JOIN sales_persons sp ON sp.sales_person_id = d.sales_person_id
        GROUP BY d.dealer_id, d.name, d.city, d.latitude, d.longitude, d.category,
                 dhs.health_status, sp.name
        ORDER BY revenue DESC
    """)
    rows = fmt_r(cur.fetchall())
    # Normalize health status to lowercase for frontend
    for r in rows:
        r["health"] = (r["health"] or "unknown").lower().replace("_", "-")
        r["revenue"] = float(r["revenue"] or 0)
        r["collections"] = float(r["collections"] or 0)
        r["outstanding"] = float(r["outstanding"] or 0)
        r["lat"] = float(r["lat"] or 0)
        r["lng"] = float(r["lng"] or 0)
        r["pending_commitments"] = int(r["pending_commitments"] or 0)
        r["last_visit"] = str(r["last_visit"]) if r["last_visit"] else "No visits"
    conn.close()
    return rows


# ─── /api/revenue-chart ───────────────────────────────────────────────────────
@app.get("/api/revenue-chart")
def get_revenue_chart():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            TO_CHAR(order_date::date, 'Mon') AS month,
            TO_CHAR(order_date::date, 'YYYY-MM') AS ym,
            SUM(total_amount) AS revenue,
            COUNT(*) AS order_count
        FROM orders
        GROUP BY TO_CHAR(order_date::date, 'YYYY-MM'), TO_CHAR(order_date::date, 'Mon')
        ORDER BY ym
    """)
    revenue_rows = fmt_r(cur.fetchall())

    cur.execute("""
        SELECT
            TO_CHAR(payment_date::date, 'Mon') AS month,
            TO_CHAR(payment_date::date, 'YYYY-MM') AS ym,
            SUM(amount) AS collections
        FROM payments
        GROUP BY TO_CHAR(payment_date::date, 'YYYY-MM'), TO_CHAR(payment_date::date, 'Mon')
        ORDER BY ym
    """)
    collections_by_month = {r["ym"]: float(r["collections"]) for r in cur.fetchall()}

    cur.execute("""
        SELECT
            TO_CHAR(period_start::date, 'Mon') AS month,
            TO_CHAR(period_start::date, 'YYYY-MM') AS ym,
            SUM(target_amount) AS target
        FROM sales_targets
        GROUP BY TO_CHAR(period_start::date, 'YYYY-MM'), TO_CHAR(period_start::date, 'Mon')
        ORDER BY ym
    """)
    targets = {r["ym"]: float(r["target"]) for r in cur.fetchall()}

    result = []
    for r in revenue_rows:
        ym = r["ym"]
        result.append({
            "month": r["month"],
            "revenue": float(r["revenue"]),
            "collections": collections_by_month.get(ym, 0),
            "target": targets.get(ym, float(r["revenue"]) * 1.1),
        })

    conn.close()
    return result


# ─── /api/commitment-pipeline ─────────────────────────────────────────────────
@app.get("/api/commitment-pipeline")
def get_commitment_pipeline():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            c.status,
            COUNT(*) AS cnt,
            COALESCE(SUM(c.quantity_promised * p.dealer_price), 0) AS value
        FROM commitments c
        LEFT JOIN products p ON c.product_id = p.product_id
        GROUP BY c.status ORDER BY c.status
    """)
    rows = fmt_r(cur.fetchall())
    STATUS_COLORS = {
        "CONVERTED": "#22c55e", "PENDING": "#f59e0b", "PARTIAL": "#6366f1",
        "EXPIRED": "#ef4444", "CANCELLED": "#8b8fad"
    }
    for r in rows:
        r["value"] = float(r["value"])
        r["color"] = STATUS_COLORS.get(r["status"], "#8b8fad")
        r["status"] = r["status"].capitalize()
    conn.close()
    return rows


# ─── /api/sales-team ──────────────────────────────────────────────────────────
@app.get("/api/sales-team")
def get_sales_team():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            sp.sales_person_id,
            sp.name,
            STRING_AGG(DISTINCT t.name, ' / ') AS territory,
            COUNT(DISTINCT d.dealer_id) AS dealers,
            COUNT(DISTINCT v.visit_id) AS visits,
            COALESCE(SUM(DISTINCT st.target_amount), 0) AS target,
            COALESCE(SUM(o.total_amount), 0) AS achieved,
            COUNT(DISTINCT c.commitment_id) AS commitments,
            CASE
                WHEN COUNT(DISTINCT c.commitment_id) > 0 THEN
                    ROUND(COUNT(DISTINCT CASE WHEN c.status = 'CONVERTED' THEN c.commitment_id END) * 100.0
                    / COUNT(DISTINCT c.commitment_id))
                ELSE 0
            END AS conversion
        FROM sales_persons sp
        LEFT JOIN territory_assignments ta ON ta.sales_person_id = sp.sales_person_id
        LEFT JOIN territories t ON t.territory_id = ta.territory_id
        LEFT JOIN dealers d ON d.sales_person_id = sp.sales_person_id
        LEFT JOIN visits v ON v.sales_person_id = sp.sales_person_id
            AND v.visit_date >= (CURRENT_DATE - INTERVAL '30 days')::text
        LEFT JOIN sales_targets st ON st.sales_person_id = sp.sales_person_id
        LEFT JOIN orders o ON o.dealer_id = d.dealer_id
            AND o.order_date >= (CURRENT_DATE - INTERVAL '30 days')::text
        LEFT JOIN commitments c ON c.sales_person_id = sp.sales_person_id
        GROUP BY sp.sales_person_id, sp.name
        ORDER BY achieved DESC
    """)
    rows = fmt_r(cur.fetchall())
    for r in rows:
        r["target"] = float(r["target"] or 0)
        r["achieved"] = float(r["achieved"] or 0)
        r["conversion"] = int(r["conversion"] or 0)
    conn.close()
    return rows


# ─── /api/recent-activity ─────────────────────────────────────────────────────
@app.get("/api/recent-activity")
def get_recent_activity():
    conn = get_conn()
    cur = conn.cursor()

    activities = []

    cur.execute("""
        SELECT v.visit_date AS ts, d.name AS dealer, sp.name AS rep,
               v.notes AS detail
        FROM visits v
        JOIN dealers d ON d.dealer_id = v.dealer_id
        JOIN sales_persons sp ON sp.sales_person_id = v.sales_person_id
        ORDER BY v.visit_date DESC LIMIT 4
    """)
    for r in cur.fetchall():
        activities.append({
            "type": "visit", "icon": "visit",
            "text": f"{r['rep']} visited {r['dealer']}",
            "detail": r["detail"] or "Visit completed",
            "time": str(r["ts"]),
        })

    cur.execute("""
        SELECT o.order_date AS ts, d.name AS dealer, o.total_amount AS amount,
               o.status AS status
        FROM orders o
        JOIN dealers d ON d.dealer_id = o.dealer_id
        ORDER BY o.order_date DESC LIMIT 3
    """)
    for r in cur.fetchall():
        activities.append({
            "type": "order", "icon": "order",
            "text": f"Order {r['status'].lower()}: {r['dealer']}",
            "detail": f"₹{float(r['amount']):,.0f}",
            "time": str(r["ts"]),
        })

    cur.execute("""
        SELECT al.created_at AS ts, d.name AS dealer, al.message AS msg, al.severity
        FROM alerts al
        JOIN dealers d ON d.dealer_id = al.dealer_id
        WHERE al.is_active = TRUE
        ORDER BY al.created_at DESC LIMIT 3
    """)
    for r in cur.fetchall():
        activities.append({
            "type": "alert", "icon": "alert",
            "text": f"{r['dealer']} flagged {r['severity'].lower()}",
            "detail": r["msg"],
            "time": str(r["ts"]),
        })

    # Sort all by time desc
    activities.sort(key=lambda x: x["time"], reverse=True)
    conn.close()
    return activities[:8]


# ─── /api/weekly-pipeline ─────────────────────────────────────────────────────
@app.get("/api/weekly-pipeline")
def get_weekly_pipeline():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT
            'W' || EXTRACT(WEEK FROM commitment_date::date)::int %% 4 + 1 AS week,
            COUNT(CASE WHEN status = 'PENDING' THEN 1 END) AS new,
            COUNT(CASE WHEN status = 'PARTIAL' THEN 1 END) AS confirmed,
            COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) AS fulfilled,
            COUNT(CASE WHEN status = 'EXPIRED' THEN 1 END) AS overdue
        FROM commitments
        WHERE commitment_date >= (CURRENT_DATE - INTERVAL '28 days')::text
        GROUP BY week ORDER BY week
    """)
    rows = fmt_r(cur.fetchall())
    conn.close()
    return rows or [
        {"week": "W1", "new": 0, "confirmed": 0, "fulfilled": 0, "overdue": 0}
    ]


if __name__ == "__main__":
    print("Starting SupplyChain Copilot API on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
