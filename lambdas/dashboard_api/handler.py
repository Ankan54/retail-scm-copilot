"""
Dashboard API Lambda Handler
Serves the React manager dashboard with real-time data from PostgreSQL.

Endpoints (all accept optional ?month=YYYY-MM):
  GET /api/metrics             — KPI summary cards + prev-month trend
  GET /api/dealers             — Dealer list with health/revenue/outstanding
  GET /api/revenue-chart       — Monthly revenue/collections/target
  GET /api/commitment-pipeline — Commitment status breakdown (donut chart)
  GET /api/sales-team          — Sales rep performance table
  GET /api/recent-activity     — Latest visits, orders, alerts feed
  GET /api/weekly-pipeline     — Weekly commitment counts (bar chart)
"""

import json
import logging
import calendar
from datetime import date as _date

logger = logging.getLogger()
logger.setLevel(logging.INFO)

import sys
sys.path.insert(0, "/opt/python")
sys.path.insert(0, "/var/task")

from shared.db_utils import get_db, _serialize


# ─── Month range helper ────────────────────────────────────────────────────────

def _month_range(month_str):
    """
    Given '2026-02', returns (curr_start, curr_end, prev_start, prev_end)
    as 'YYYY-MM-DD' strings for the selected month and the one before it.
    """
    year, mon = int(month_str[:4]), int(month_str[5:7])
    last = calendar.monthrange(year, mon)[1]
    cs = f"{year:04d}-{mon:02d}-01"
    ce = f"{year:04d}-{mon:02d}-{last:02d}"
    py, pm = (year - 1, 12) if mon == 1 else (year, mon - 1)
    pl = calendar.monthrange(py, pm)[1]
    ps = f"{py:04d}-{pm:02d}-01"
    pe = f"{py:04d}-{pm:02d}-{pl:02d}"
    return cs, ce, ps, pe


def _default_month_range():
    """Returns range for current month and previous month."""
    today = _date.today()
    return _month_range(today.strftime("%Y-%m"))


# ─── Lambda entry point ────────────────────────────────────────────────────────

def lambda_handler(event, context):
    path = event.get("path", event.get("rawPath", ""))
    method = event.get("httpMethod", event.get("requestContext", {}).get("http", {}).get("method", "GET"))
    logger.info(f"{method} {path}")

    if method == "OPTIONS":
        return _resp(200, {})

    query_params = event.get("queryStringParameters") or {}
    month = query_params.get("month")  # e.g. "2026-02", None = current month

    try:
        if "/api/metrics" in path:
            data = get_metrics(month)
        elif "/api/dealers" in path:
            data = get_dealers()
        elif "/api/revenue-chart" in path:
            data = get_revenue_chart()
        elif "/api/commitment-pipeline" in path:
            data = get_commitment_pipeline(month)
        elif "/api/sales-team" in path:
            data = get_sales_team(month)
        elif "/api/recent-activity" in path:
            data = get_recent_activity(month)
        elif "/api/weekly-pipeline" in path:
            data = get_weekly_pipeline(month)
        else:
            data = {"error": f"Unknown path: {path}"}

        return _resp(200, data)
    except Exception as e:
        logger.exception("Dashboard API error")
        return _resp(500, {"error": str(e)})


def _resp(status_code, data):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET,OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
        },
        "body": json.dumps(data, default=_serialize),
    }


def _one(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    row = cur.fetchone()
    return dict(row) if row else {}


def _all(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return [dict(r) for r in cur.fetchall()]


# ─── /api/metrics ─────────────────────────────────────────────────────────────

def get_metrics(month=None):
    cs, ce, ps, pe = _month_range(month) if month else _default_month_range()
    conn = get_db()
    try:
        # Current period revenue & collections
        revenue = float(_one(conn,
            "SELECT COALESCE(SUM(total_amount),0) AS v FROM orders WHERE order_date >= %s AND order_date <= %s",
            (cs, ce)).get("v", 0))

        prev_revenue = float(_one(conn,
            "SELECT COALESCE(SUM(total_amount),0) AS v FROM orders WHERE order_date >= %s AND order_date <= %s",
            (ps, pe)).get("v", 0))

        collections = float(_one(conn,
            "SELECT COALESCE(SUM(amount),0) AS v FROM payments WHERE payment_date >= %s AND payment_date <= %s",
            (cs, ce)).get("v", 0))

        prev_collections = float(_one(conn,
            "SELECT COALESCE(SUM(amount),0) AS v FROM payments WHERE payment_date >= %s AND payment_date <= %s",
            (ps, pe)).get("v", 0))

        # Point-in-time counts (not period-filtered)
        active_dealers = int(_one(conn,
            "SELECT COUNT(*) AS v FROM dealers WHERE status = 'ACTIVE'"
        ).get("v", 0))

        at_risk = int(_one(conn, """
            SELECT COUNT(*) AS v FROM (
                SELECT DISTINCT ON (dealer_id) health_status
                FROM dealer_health_scores
                ORDER BY dealer_id, calculated_date DESC
            ) s WHERE health_status IN ('AT_RISK', 'CRITICAL')
        """).get("v", 0))

        # Visits within period
        visited = int(_one(conn,
            "SELECT COUNT(DISTINCT dealer_id) AS v FROM visits WHERE visit_date >= %s AND visit_date <= %s",
            (cs, ce)).get("v", 0))

        prev_visited = int(_one(conn,
            "SELECT COUNT(DISTINCT dealer_id) AS v FROM visits WHERE visit_date >= %s AND visit_date <= %s",
            (ps, pe)).get("v", 0))

        # Active pipeline (point-in-time)
        pipeline = _one(conn, """
            SELECT COUNT(*) AS cnt,
                   COALESCE(SUM(c.quantity_promised * p.dealer_price), 0) AS val
            FROM commitments c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.status IN ('PENDING', 'PARTIAL')
        """)

        prev_pipeline = _one(conn, """
            SELECT COUNT(*) AS cnt,
                   COALESCE(SUM(c.quantity_promised * p.dealer_price), 0) AS val
            FROM commitments c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.status IN ('PENDING', 'PARTIAL')
              AND c.commitment_date >= %s AND c.commitment_date <= %s
        """, (ps, pe))

        # Target for selected month
        target = float(_one(conn,
            "SELECT COALESCE(SUM(target_value),0) AS v FROM sales_targets WHERE TO_CHAR(period_start::date,'YYYY-MM') = %s",
            (cs[:7],)).get("v") or 4200000)

        pipeline_value = float(pipeline.get("val", 0))
        prev_pipeline_value = float(prev_pipeline.get("val", 0))

        return {
            "revenue":          revenue,
            "collections":      collections,
            "active_dealers":   active_dealers,
            "at_risk":          at_risk,
            "visited_30d":      visited,
            "pipeline_count":   int(pipeline.get("cnt", 0)),
            "pipeline_value":   pipeline_value,
            "monthly_target":   target,
            "target_pct":       round(collections / target * 100, 1) if target else 0,
            # Previous period — used by frontend for trend arrows
            "prev_revenue":         prev_revenue,
            "prev_collections":     prev_collections,
            "prev_visited":         prev_visited,
            "prev_pipeline_count":  int(prev_pipeline.get("cnt", 0)),
            "prev_pipeline_value":  prev_pipeline_value,
        }
    finally:
        conn.close()


# ─── /api/dealers ─────────────────────────────────────────────────────────────

def get_dealers():
    conn = get_db()
    try:
        rows = _all(conn, """
            WITH
            latest_health AS (
                SELECT DISTINCT ON (dealer_id) dealer_id, health_status
                FROM dealer_health_scores
                ORDER BY dealer_id, calculated_date DESC
            ),
            recent_revenue AS (
                SELECT dealer_id, SUM(total_amount) AS revenue
                FROM orders
                WHERE order_date >= (CURRENT_DATE - INTERVAL '30 days')::text
                GROUP BY dealer_id
            ),
            recent_collections AS (
                SELECT dealer_id, SUM(amount) AS collections
                FROM payments
                WHERE payment_date >= (CURRENT_DATE - INTERVAL '30 days')::text
                GROUP BY dealer_id
            ),
            pending_outstanding AS (
                SELECT dealer_id, SUM(total_amount) AS outstanding
                FROM orders WHERE payment_status = 'PENDING'
                GROUP BY dealer_id
            ),
            last_visits AS (
                SELECT dealer_id, MAX(visit_date) AS last_visit
                FROM visits GROUP BY dealer_id
            ),
            pending_commits AS (
                SELECT dealer_id, COUNT(*) AS pending_commitments
                FROM commitments WHERE status = 'PENDING'
                GROUP BY dealer_id
            )
            SELECT
                d.dealer_id AS id,
                d.name,
                d.city,
                d.latitude  AS lat,
                d.longitude AS lng,
                d.category,
                COALESCE(lh.health_status, 'UNKNOWN')    AS health,
                COALESCE(rr.revenue, 0)                  AS revenue,
                COALESCE(rc.collections, 0)              AS collections,
                COALESCE(po.outstanding, 0)              AS outstanding,
                lv.last_visit,
                COALESCE(pc.pending_commitments, 0)      AS pending_commitments,
                sp.name AS sales_rep
            FROM dealers d
            LEFT JOIN latest_health      lh ON lh.dealer_id = d.dealer_id
            LEFT JOIN recent_revenue     rr ON rr.dealer_id = d.dealer_id
            LEFT JOIN recent_collections rc ON rc.dealer_id = d.dealer_id
            LEFT JOIN pending_outstanding po ON po.dealer_id = d.dealer_id
            LEFT JOIN last_visits        lv ON lv.dealer_id = d.dealer_id
            LEFT JOIN pending_commits    pc ON pc.dealer_id = d.dealer_id
            LEFT JOIN sales_persons      sp ON sp.sales_person_id = d.sales_person_id
            ORDER BY revenue DESC
        """)

        for r in rows:
            r["health"] = (r.get("health") or "unknown").lower().replace("_", "-")
            r["revenue"] = float(r.get("revenue") or 0)
            r["collections"] = float(r.get("collections") or 0)
            r["outstanding"] = float(r.get("outstanding") or 0)
            r["lat"] = float(r.get("lat") or 0)
            r["lng"] = float(r.get("lng") or 0)
            r["pending_commitments"] = int(r.get("pending_commitments") or 0)
            lv = r.get("last_visit")
            r["last_visit"] = str(lv) if lv else "No visits"

        return rows
    finally:
        conn.close()


# ─── /api/revenue-chart ───────────────────────────────────────────────────────

def get_revenue_chart():
    conn = get_db()
    try:
        rev_rows = _all(conn, """
            SELECT
                TO_CHAR(order_date::date, 'Mon')     AS month,
                TO_CHAR(order_date::date, 'YYYY-MM') AS ym,
                SUM(total_amount) AS revenue
            FROM orders
            GROUP BY ym, month
            ORDER BY ym
        """)

        coll_map = {r["ym"]: float(r["collections"]) for r in _all(conn, """
            SELECT TO_CHAR(payment_date::date, 'YYYY-MM') AS ym,
                   SUM(amount) AS collections
            FROM payments GROUP BY ym
        """)}

        target_map = {r["ym"]: float(r["target"]) for r in _all(conn, """
            SELECT TO_CHAR(period_start::date, 'YYYY-MM') AS ym,
                   SUM(target_value) AS target
            FROM sales_targets GROUP BY ym
        """)}

        result = []
        for r in rev_rows:
            ym = r["ym"]
            rev = float(r["revenue"])
            result.append({
                "month": r["month"],
                "ym":    ym,
                "revenue":     rev,
                "collections": coll_map.get(ym, 0),
                "target":      target_map.get(ym, round(rev * 1.1)),
            })
        return result
    finally:
        conn.close()


# ─── /api/commitment-pipeline ─────────────────────────────────────────────────

def get_commitment_pipeline(month=None):
    STATUS_COLORS = {
        "CONVERTED":  "#22c55e",
        "PENDING":    "#f59e0b",
        "PARTIAL":    "#6366f1",
        "EXPIRED":    "#ef4444",
        "CANCELLED":  "#8b8fad",
    }
    cs, ce, _, _ = _month_range(month) if month else _default_month_range()
    conn = get_db()
    try:
        rows = _all(conn, """
            SELECT c.status,
                   COUNT(*) AS cnt,
                   COALESCE(SUM(c.quantity_promised * p.dealer_price), 0) AS value
            FROM commitments c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.commitment_date >= %s AND c.commitment_date <= %s
            GROUP BY c.status
            ORDER BY c.status
        """, (cs, ce))
        for r in rows:
            r["value"] = float(r.get("value") or 0)
            r["color"] = STATUS_COLORS.get(r["status"], "#8b8fad")
            r["status"] = r["status"].capitalize()
        return rows
    finally:
        conn.close()


# ─── /api/sales-team ──────────────────────────────────────────────────────────

def get_sales_team(month=None):
    cs, ce, ps, pe = _month_range(month) if month else _default_month_range()
    conn = get_db()
    try:
        rows = _all(conn, """
            WITH
            rep_territories AS (
                SELECT ta.sales_person_id,
                       STRING_AGG(DISTINCT t.name, ' / ') AS territory
                FROM territory_assignments ta
                LEFT JOIN territories t ON t.territory_id = ta.territory_id
                GROUP BY ta.sales_person_id
            ),
            rep_dealers AS (
                SELECT sales_person_id, COUNT(*) AS dealers
                FROM dealers GROUP BY sales_person_id
            ),
            rep_visits AS (
                SELECT sales_person_id, COUNT(*) AS visits
                FROM visits
                WHERE visit_date >= %s AND visit_date <= %s
                GROUP BY sales_person_id
            ),
            rep_targets AS (
                SELECT sales_person_id, SUM(target_value) AS target
                FROM sales_targets
                WHERE TO_CHAR(period_start::date,'YYYY-MM') = %s
                GROUP BY sales_person_id
            ),
            rep_orders AS (
                SELECT d.sales_person_id, SUM(o.total_amount) AS achieved
                FROM orders o
                JOIN dealers d ON d.dealer_id = o.dealer_id
                WHERE o.order_date >= %s AND o.order_date <= %s
                GROUP BY d.sales_person_id
            ),
            rep_commitments AS (
                SELECT sales_person_id,
                       COUNT(*) AS commitments,
                       ROUND(
                           COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END)
                           * 100.0 / NULLIF(COUNT(*), 0)
                       ) AS conversion
                FROM commitments
                GROUP BY sales_person_id
            )
            SELECT
                sp.sales_person_id,
                sp.name,
                COALESCE(rt.territory, '—')  AS territory,
                COALESCE(rd.dealers, 0)       AS dealers,
                COALESCE(rv.visits, 0)        AS visits,
                COALESCE(rtar.target, 0)      AS target,
                COALESCE(ro.achieved, 0)      AS achieved,
                COALESCE(rc.commitments, 0)   AS commitments,
                COALESCE(rc.conversion, 0)    AS conversion
            FROM sales_persons sp
            LEFT JOIN rep_territories rt   ON rt.sales_person_id   = sp.sales_person_id
            LEFT JOIN rep_dealers     rd   ON rd.sales_person_id   = sp.sales_person_id
            LEFT JOIN rep_visits      rv   ON rv.sales_person_id   = sp.sales_person_id
            LEFT JOIN rep_targets     rtar ON rtar.sales_person_id = sp.sales_person_id
            LEFT JOIN rep_orders      ro   ON ro.sales_person_id   = sp.sales_person_id
            LEFT JOIN rep_commitments rc   ON rc.sales_person_id   = sp.sales_person_id
            ORDER BY achieved DESC
        """, (cs, ce, cs[:7], cs, ce))
        for r in rows:
            r["target"]     = float(r.get("target") or 0)
            r["achieved"]   = float(r.get("achieved") or 0)
            r["conversion"] = int(r.get("conversion") or 0)
        return rows
    finally:
        conn.close()


# ─── /api/recent-activity ─────────────────────────────────────────────────────

def get_recent_activity(month=None):
    cs, ce, ps, pe = _month_range(month) if month else _default_month_range()
    conn = get_db()
    try:
        activities = []

        for r in _all(conn, """
            SELECT v.visit_date AS ts, d.name AS dealer,
                   sp.name AS rep, v.raw_notes AS detail
            FROM visits v
            JOIN dealers d        ON d.dealer_id        = v.dealer_id
            JOIN sales_persons sp ON sp.sales_person_id = v.sales_person_id
            WHERE v.visit_date >= %s AND v.visit_date <= %s
            ORDER BY v.visit_date DESC LIMIT 4
        """, (cs, ce)):
            activities.append({
                "type": "visit", "icon": "visit",
                "text":   f"{r['rep']} visited {r['dealer']}",
                "detail": r["detail"] or "Visit completed",
                "time":   str(r["ts"]),
            })

        for r in _all(conn, """
            SELECT o.order_date AS ts, d.name AS dealer,
                   o.total_amount AS amount, o.status
            FROM orders o
            JOIN dealers d ON d.dealer_id = o.dealer_id
            WHERE o.order_date >= %s AND o.order_date <= %s
            ORDER BY o.order_date DESC LIMIT 3
        """, (cs, ce)):
            activities.append({
                "type": "order", "icon": "order",
                "text":   f"Order {r['status'].lower()}: {r['dealer']}",
                "detail": f"₹{float(r['amount']):,.0f}",
                "time":   str(r["ts"]),
            })

        for r in _all(conn, """
            SELECT al.created_at AS ts, d.name AS dealer,
                   al.message AS msg, al.priority AS severity
            FROM alerts al
            JOIN dealers d ON d.dealer_id = al.entity_id
                           AND al.entity_type = 'dealer'
            WHERE al.status = 'ACTIVE'
            ORDER BY al.created_at DESC LIMIT 3
        """):
            activities.append({
                "type": "alert", "icon": "alert",
                "text":   f"{r['dealer']} flagged {(r['severity'] or 'low').lower()}",
                "detail": r["msg"],
                "time":   str(r["ts"]),
            })

        activities.sort(key=lambda x: x["time"], reverse=True)
        return activities[:8]
    finally:
        conn.close()


# ─── /api/weekly-pipeline ─────────────────────────────────────────────────────

def get_weekly_pipeline(month=None):
    cs, ce, ps, pe = _month_range(month) if month else _default_month_range()
    conn = get_db()
    try:
        rows = _all(conn, """
            SELECT
                'W' || (EXTRACT(WEEK FROM commitment_date::date)::int %% 4 + 1) AS week,
                COUNT(CASE WHEN status = 'PENDING'   THEN 1 END) AS new,
                COUNT(CASE WHEN status = 'PARTIAL'   THEN 1 END) AS confirmed,
                COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) AS fulfilled,
                COUNT(CASE WHEN status = 'EXPIRED'   THEN 1 END) AS overdue
            FROM commitments
            WHERE commitment_date >= %s AND commitment_date <= %s
            GROUP BY week
            ORDER BY week
        """, (cs, ce))
        return rows or [{"week": "W1", "new": 0, "confirmed": 0, "fulfilled": 0, "overdue": 0}]
    finally:
        conn.close()
