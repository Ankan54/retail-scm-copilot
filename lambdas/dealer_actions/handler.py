"""
Dealer Action Group Lambda Handler (PostgreSQL version)
Handles: resolve_entity, get_dealer_profile, get_payment_status,
         get_order_history, get_dealer_health_score, suggest_visit_plan,
         get_rep_dashboard
"""
import json
import sys
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sys.path.insert(0, "/opt/python")
sys.path.insert(0, "/var/task")

from shared.db_utils import get_db, bedrock_response, rows_to_list, row_to_dict, today

try:
    from rapidfuzz import fuzz, process as fuzz_process
    FUZZY_AVAILABLE = True
except ImportError:
    FUZZY_AVAILABLE = False
    logger.warning("rapidfuzz not installed - fuzzy matching disabled")


def lambda_handler(event, context):
    """Main entry point for Bedrock Agent action group."""
    logger.info(f"Event: {json.dumps(event, default=str)}")

    action_group = event.get("actionGroup", "dealer_actions")
    function = event.get("function", "")
    params = {p["name"]: p["value"] for p in event.get("parameters", [])}

    try:
        if function == "resolve_entity":
            result = resolve_entity(
                params["entity_type"],
                params["entity_name"],
                params.get("sales_person_id"),
            )
        elif function == "get_dealer_profile":
            result = get_dealer_profile(params["dealer_id"])
        elif function == "get_payment_status":
            result = get_payment_status(params["dealer_id"])
        elif function == "get_order_history":
            result = get_order_history(params["dealer_id"], int(params.get("limit", 5)))
        elif function == "get_dealer_health_score":
            result = get_dealer_health_score(params["dealer_id"])
        elif function == "suggest_visit_plan":
            result = suggest_visit_plan(
                params["sales_person_id"], int(params.get("max_dealers", 5))
            )
        elif function == "get_rep_dashboard":
            result = get_rep_dashboard(params["sales_person_id"])
        else:
            result = {"error": f"Unknown function: {function}"}

    except KeyError as e:
        result = {"error": f"Missing required parameter: {e}"}
    except Exception as e:
        logger.exception(f"Error in {function}")
        result = {"error": str(e)}

    return bedrock_response(action_group, function, result)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _fetchone(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur.fetchone()

def _fetchall(conn, sql, args=()):
    cur = conn.cursor()
    cur.execute(sql, args)
    return cur.fetchall()


# ─── resolve_entity ───────────────────────────────────────────────────────────

def resolve_entity(entity_type: str, entity_name: str, sales_person_id: str = None) -> dict:
    """Fuzzy-match entity name to DB record."""
    conn = get_db()
    try:
        if entity_type == "dealer":
            if sales_person_id:
                rows = _fetchall(conn,
                    "SELECT dealer_id, name FROM dealers WHERE sales_person_id = %s AND status = 'ACTIVE'",
                    (sales_person_id,))
            else:
                rows = _fetchall(conn,
                    "SELECT dealer_id, name FROM dealers WHERE status = 'ACTIVE'")
            entities = {r["dealer_id"]: r["name"] for r in rows}
            id_field = "dealer_id"

        elif entity_type == "product":
            rows = _fetchall(conn,
                "SELECT product_id, name, product_code, short_name FROM products WHERE status = 'ACTIVE'")
            entities = {r["product_id"]: r["name"] for r in rows}
            id_field = "product_id"

        else:
            return {"error": f"Unknown entity_type: {entity_type}"}

        if not entities:
            return {"confidence": 0, "candidates": [], "error": "No entities found"}

        if FUZZY_AVAILABLE:
            matches = fuzz_process.extract(
                entity_name, entities, scorer=fuzz.token_sort_ratio, limit=3
            )
            if matches and matches[0][1] >= 70:
                best = matches[0]
                return {
                    "success": True,
                    id_field: best[2],
                    "entity_name": best[0],
                    "confidence": best[1] / 100,
                    "candidates": [{"id": m[2], "name": m[0], "score": m[1]} for m in matches],
                }
            else:
                return {
                    "success": False,
                    "confidence": (matches[0][1] / 100) if matches else 0,
                    "message": f"No confident match for '{entity_name}'. Did you mean one of these?",
                    "candidates": [{"id": m[2], "name": m[0], "score": m[1]} for m in matches],
                }
        else:
            entity_name_lower = entity_name.lower()
            matches = [
                (eid, name) for eid, name in entities.items()
                if entity_name_lower in name.lower() or name.lower() in entity_name_lower
            ]
            if matches:
                eid, name = matches[0]
                return {
                    "success": True,
                    id_field: eid,
                    "entity_name": name,
                    "confidence": 0.8,
                    "candidates": [{"id": e[0], "name": e[1]} for e in matches[:3]],
                }
            return {"success": False, "confidence": 0, "candidates": []}
    finally:
        conn.close()


# ─── get_dealer_profile ───────────────────────────────────────────────────────

def get_dealer_profile(dealer_id: str) -> dict:
    """Get complete dealer profile."""
    conn = get_db()
    try:
        row = _fetchone(conn,
            """
            SELECT d.*,
                   t.name AS territory_name,
                   sp.name AS sales_rep_name,
                   sp.phone AS sales_rep_phone
            FROM dealers d
            LEFT JOIN territories t ON d.territory_id = t.territory_id
            LEFT JOIN sales_persons sp ON d.sales_person_id = sp.sales_person_id
            WHERE d.dealer_id = %s
            """,
            (dealer_id,))
        if not row:
            return {"error": f"Dealer not found: {dealer_id}"}
        return {"success": True, "dealer": row_to_dict(row)}
    finally:
        conn.close()


# ─── get_payment_status ───────────────────────────────────────────────────────

def get_payment_status(dealer_id: str) -> dict:
    """Get dealer payment status: outstanding, overdue, overdue days."""
    conn = get_db()
    try:
        row = _fetchone(conn,
            """
            SELECT
                COALESCE(SUM(CASE WHEN i.status != 'PAID' THEN i.total_amount - i.amount_paid ELSE 0 END), 0) AS outstanding_amount,
                COALESCE(SUM(CASE
                    WHEN i.status IN ('OVERDUE') THEN i.total_amount - i.amount_paid
                    WHEN i.status = 'PENDING' AND i.due_date < CURRENT_DATE::text THEN i.total_amount - i.amount_paid
                    ELSE 0
                END), 0) AS overdue_amount,
                COALESCE(MAX(CASE
                    WHEN i.due_date < CURRENT_DATE::text AND i.status != 'PAID'
                    THEN (CURRENT_DATE - i.due_date::date)
                    ELSE 0
                END), 0) AS max_days_overdue,
                COUNT(CASE WHEN i.status != 'PAID' THEN 1 END) AS open_invoices,
                COUNT(CASE WHEN i.status = 'OVERDUE' OR (i.status = 'PENDING' AND i.due_date < CURRENT_DATE::text) THEN 1 END) AS overdue_invoices
            FROM invoices i
            WHERE i.dealer_id = %s
            """,
            (dealer_id,))

        recent_payments = _fetchall(conn,
            """
            SELECT payment_date, amount, payment_mode, notes
            FROM payments WHERE dealer_id = %s
            ORDER BY payment_date DESC LIMIT 5
            """,
            (dealer_id,))

        return {
            "success": True,
            "dealer_id": dealer_id,
            "outstanding_amount": float(row["outstanding_amount"] or 0),
            "overdue_amount": float(row["overdue_amount"] or 0),
            "max_days_overdue": int(row["max_days_overdue"] or 0),
            "open_invoices": int(row["open_invoices"] or 0),
            "overdue_invoices": int(row["overdue_invoices"] or 0),
            "recent_payments": rows_to_list(recent_payments),
        }
    finally:
        conn.close()


# ─── get_order_history ────────────────────────────────────────────────────────

def get_order_history(dealer_id: str, limit: int = 5) -> dict:
    """Get recent orders for a dealer."""
    conn = get_db()
    try:
        orders = _fetchall(conn,
            """
            SELECT o.order_number, o.order_date, o.total_amount, o.status,
                   o.payment_status, o.source,
                   STRING_AGG(p.short_name || ' x' || oi.quantity_ordered::text, ', ') AS items_summary
            FROM orders o
            LEFT JOIN order_items oi ON o.order_id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.product_id
            WHERE o.dealer_id = %s
            GROUP BY o.order_id, o.order_number, o.order_date, o.total_amount,
                     o.status, o.payment_status, o.source
            ORDER BY o.order_date DESC
            LIMIT %s
            """,
            (dealer_id, limit))

        commitments = _fetchall(conn,
            """
            SELECT c.commitment_date, c.expected_order_date, c.quantity_promised,
                   c.status, p.short_name AS product_name
            FROM commitments c
            LEFT JOIN products p ON c.product_id = p.product_id
            WHERE c.dealer_id = %s AND c.status IN ('PENDING', 'PARTIAL')
            ORDER BY c.expected_order_date ASC LIMIT 5
            """,
            (dealer_id,))

        return {
            "success": True,
            "dealer_id": dealer_id,
            "recent_orders": rows_to_list(orders),
            "pending_commitments": rows_to_list(commitments),
        }
    finally:
        conn.close()


# ─── get_dealer_health_score ──────────────────────────────────────────────────

def get_dealer_health_score(dealer_id: str) -> dict:
    """Return precomputed health score or calculate on-the-fly."""
    conn = get_db()
    try:
        precomputed = _fetchone(conn,
            """
            SELECT overall_score, health_status, payment_score, order_frequency_score,
                   commitment_score, engagement_score, total_outstanding,
                   days_since_last_order, days_since_last_visit,
                   commitment_fulfillment_rate_90d, attention_reason
            FROM dealer_health_scores
            WHERE dealer_id = %s
            ORDER BY calculated_date DESC LIMIT 1
            """,
            (dealer_id,))

        if precomputed:
            return {
                "success": True,
                "dealer_id": dealer_id,
                "score": float(precomputed["overall_score"] or 0),
                "status": precomputed["health_status"],
                "components": {
                    "payment": float(precomputed["payment_score"] or 0),
                    "order_frequency": float(precomputed["order_frequency_score"] or 0),
                    "commitment": float(precomputed["commitment_score"] or 0),
                    "engagement": float(precomputed["engagement_score"] or 0),
                },
                "days_since_last_order": precomputed["days_since_last_order"],
                "days_since_last_visit": precomputed["days_since_last_visit"],
                "total_outstanding": float(precomputed["total_outstanding"] or 0),
                "attention_reason": precomputed["attention_reason"],
                "source": "precomputed",
            }

        # Fallback: compute on-the-fly
        scores = {}
        reasons = []

        # 1. Order Recency (25%)
        order_row = _fetchone(conn,
            """
            SELECT MAX(order_date) AS last_order, COUNT(*) AS order_count_6m
            FROM orders
            WHERE dealer_id = %s
              AND order_date >= (CURRENT_DATE - INTERVAL '6 months')::text
            """,
            (dealer_id,))

        if order_row["last_order"]:
            last_order_dt = datetime.strptime(order_row["last_order"][:10], "%Y-%m-%d")
            days_since = (datetime.now() - last_order_dt).days
            recency = max(0, 100 - days_since * 2)
            if days_since > 30:
                reasons.append(f"No order in {days_since} days")
        else:
            recency = 0
            days_since = 999
            reasons.append("No recent orders")
        scores["recency"] = recency * 0.25

        # 2. Frequency (25%)
        expected = 6
        actual = order_row["order_count_6m"] or 0
        frequency = min(100, (actual / expected) * 100)
        if actual < 3:
            reasons.append("Low order frequency")
        scores["frequency"] = frequency * 0.25

        # 3. Payment (25%)
        pay_row = _fetchone(conn,
            """
            SELECT
                COUNT(CASE WHEN i.status = 'PAID' AND i.due_date >= i.updated_at THEN 1 END) AS on_time,
                COUNT(*) AS total
            FROM invoices i
            WHERE i.dealer_id = %s
              AND i.invoice_date >= (CURRENT_DATE - INTERVAL '6 months')::text
            """,
            (dealer_id,))
        if pay_row["total"] > 0:
            payment_score = (pay_row["on_time"] / pay_row["total"]) * 100
            if payment_score < 70:
                reasons.append("Payment delays")
        else:
            payment_score = 50
        scores["payment"] = payment_score * 0.25

        # 4. Commitment Fulfillment (25%)
        commit_row = _fetchone(conn,
            """
            SELECT
                COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) AS fulfilled,
                COUNT(*) AS total
            FROM commitments
            WHERE dealer_id = %s
              AND created_at >= (CURRENT_DATE - INTERVAL '6 months')::text
            """,
            (dealer_id,))
        if commit_row["total"] > 0:
            fulfill_score = (commit_row["fulfilled"] / commit_row["total"]) * 100
            if fulfill_score < 70:
                reasons.append("Low commitment conversion")
        else:
            fulfill_score = 50
        scores["fulfillment"] = fulfill_score * 0.25

        total = sum(scores.values())
        if total >= 70:
            status = "HEALTHY"
        elif total >= 50:
            status = "AT_RISK"
        else:
            status = "CRITICAL"

        return {
            "success": True,
            "dealer_id": dealer_id,
            "score": round(total),
            "status": status,
            "components": {k: round(v / 0.25) for k, v in scores.items()},
            "reasons": reasons[:3],
            "days_since_last_order": days_since if days_since < 999 else None,
            "source": "computed",
        }
    finally:
        conn.close()


# ─── suggest_visit_plan ───────────────────────────────────────────────────────

def suggest_visit_plan(sales_person_id: str, max_dealers: int = 5) -> dict:
    """Generate prioritized visit plan for today."""
    conn = get_db()
    try:
        dealers = _fetchall(conn,
            """
            SELECT d.dealer_id, d.name, d.category, d.last_order_date,
                   d.last_visit_date, d.credit_limit, d.commitment_fulfillment_rate,
                   dhs.overall_score, dhs.health_status, dhs.attention_reason,
                   dhs.total_outstanding, dhs.days_since_last_order, dhs.days_since_last_visit
            FROM dealers d
            LEFT JOIN (
                SELECT DISTINCT ON (dealer_id)
                       dealer_id, overall_score, health_status, attention_reason,
                       total_outstanding, days_since_last_order, days_since_last_visit
                FROM dealer_health_scores
                ORDER BY dealer_id, calculated_date DESC
            ) dhs ON d.dealer_id = dhs.dealer_id
            WHERE d.sales_person_id = %s AND d.status = 'ACTIVE'
            """,
            (sales_person_id,))

        overdue_map = {}
        overdue_rows = _fetchall(conn,
            """
            SELECT i.dealer_id,
                   SUM(CASE WHEN i.status = 'OVERDUE' OR (i.status = 'PENDING' AND i.due_date < CURRENT_DATE::text)
                        THEN i.total_amount - i.amount_paid ELSE 0 END) AS overdue_amount,
                   MAX(CASE WHEN i.due_date < CURRENT_DATE::text AND i.status != 'PAID'
                        THEN (CURRENT_DATE - i.due_date::date) ELSE 0 END) AS days_overdue
            FROM invoices i
            WHERE i.dealer_id IN (
                SELECT dealer_id FROM dealers WHERE sales_person_id = %s AND status = 'ACTIVE'
            )
            GROUP BY i.dealer_id
            """,
            (sales_person_id,))
        for r in overdue_rows:
            overdue_map[r["dealer_id"]] = {
                "overdue_amount": float(r["overdue_amount"] or 0),
                "days_overdue": int(r["days_overdue"] or 0),
            }

        commitment_map = {}
        commit_rows = _fetchall(conn,
            """
            SELECT dealer_id, COUNT(*) AS expiring_count
            FROM commitments
            WHERE dealer_id IN (
                SELECT dealer_id FROM dealers WHERE sales_person_id = %s AND status = 'ACTIVE'
            )
            AND status IN ('PENDING', 'PARTIAL')
            AND expected_order_date BETWEEN CURRENT_DATE::text AND (CURRENT_DATE + INTERVAL '3 days')::text
            GROUP BY dealer_id
            """,
            (sales_person_id,))
        for r in commit_rows:
            commitment_map[r["dealer_id"]] = r["expiring_count"]

        scored = []
        for d in dealers:
            did = d["dealer_id"]
            overdue = overdue_map.get(did, {})
            overdue_amount = overdue.get("overdue_amount", 0)
            days_overdue = overdue.get("days_overdue", 0)
            expiring = commitment_map.get(did, 0)
            health = float(d["overall_score"] or 50)

            dlo = d["days_since_last_order"]
            if dlo is None and d["last_order_date"]:
                try:
                    dlo = (datetime.now() - datetime.strptime(str(d["last_order_date"])[:10], "%Y-%m-%d")).days
                except Exception:
                    dlo = 60
            elif dlo is None:
                dlo = 120

            dlv = d["days_since_last_visit"]
            if dlv is None and d["last_visit_date"]:
                try:
                    dlv = (datetime.now() - datetime.strptime(str(d["last_visit_date"])[:10], "%Y-%m-%d")).days
                except Exception:
                    dlv = 30
            elif dlv is None:
                dlv = 60

            payment_urgency = min(100, days_overdue * 3 + overdue_amount / 10000)
            order_urgency = min(100, dlo * 2.5)
            visit_recency = min(100, dlv * 3)
            commit_score = min(100, expiring * 25)
            relationship_risk = max(0, 100 - health)

            priority_score = (
                payment_urgency * 0.30
                + order_urgency * 0.25
                + visit_recency * 0.15
                + commit_score * 0.15
                + relationship_risk * 0.15
            )

            if priority_score >= 70:
                priority = "HIGH"
                if payment_urgency >= 50:
                    action = f"Collect overdue payment Rs.{overdue_amount:,.0f}"
                elif expiring > 0:
                    action = f"Close {expiring} expiring commitment(s)"
                else:
                    action = "Urgent attention needed"
            elif priority_score >= 40:
                priority = "MEDIUM"
                action = f"No order in {dlo} days - check reorder" if dlo > 30 else "Regular follow-up"
            else:
                priority = "LOW"
                action = "Relationship maintenance"

            reasons = []
            if overdue_amount > 0:
                reasons.append(f"Rs.{overdue_amount:,.0f} overdue ({days_overdue}d)")
            if dlo > 30:
                reasons.append(f"No order in {dlo} days")
            if expiring > 0:
                reasons.append(f"{expiring} commitment(s) expiring soon")
            if health < 50:
                reasons.append(f"Health score critical ({health:.0f})")

            scored.append({
                "dealer_id": did,
                "name": d["name"],
                "category": d["category"],
                "priority": priority,
                "priority_score": round(priority_score),
                "suggested_action": action,
                "reasons": reasons[:3],
                "overdue_amount": overdue_amount,
                "days_since_last_order": dlo,
                "health_score": health,
                "health_status": d["health_status"],
            })

        scored.sort(key=lambda x: x["priority_score"], reverse=True)
        return {
            "success": True,
            "sales_person_id": sales_person_id,
            "plan_date": today(),
            "total_active_dealers": len(dealers),
            "recommended_visits": scored[:max_dealers],
        }
    finally:
        conn.close()


# ─── get_rep_dashboard ────────────────────────────────────────────────────────

def get_rep_dashboard(sales_person_id: str) -> dict:
    """Get sales rep performance dashboard."""
    conn = get_db()
    try:
        now = datetime.now()
        month_start = now.strftime("%Y-%m-01")

        sales_row = _fetchone(conn,
            """
            SELECT COALESCE(SUM(o.total_amount), 0) AS sales_amount,
                   COUNT(o.order_id) AS order_count
            FROM orders o
            WHERE o.sales_person_id = %s
              AND o.order_date >= %s AND o.status != 'CANCELLED'
            """,
            (sales_person_id, month_start))

        target_row = _fetchone(conn,
            """
            SELECT COALESCE(SUM(target_value), 0) AS sales_target
            FROM sales_targets
            WHERE sales_person_id = %s AND target_type = 'REVENUE'
              AND period_start <= %s AND period_end >= %s
            """,
            (sales_person_id, today(), today()))

        collection_row = _fetchone(conn,
            """
            SELECT COALESCE(SUM(amount), 0) AS collected
            FROM payments
            WHERE collected_by = %s AND payment_date >= %s
            """,
            (sales_person_id, month_start))

        visit_row = _fetchone(conn,
            """
            SELECT COUNT(DISTINCT dealer_id) AS visited_this_month
            FROM visits
            WHERE sales_person_id = %s AND visit_date >= %s
            """,
            (sales_person_id, month_start))

        total_dealers_row = _fetchone(conn,
            "SELECT COUNT(*) AS total FROM dealers WHERE sales_person_id = %s AND status = 'ACTIVE'",
            (sales_person_id,))

        followup_row = _fetchone(conn,
            """
            SELECT COUNT(*) AS pending
            FROM visits
            WHERE sales_person_id = %s AND follow_up_required = TRUE
              AND visit_date >= (CURRENT_DATE - INTERVAL '30 days')::text
              AND next_visit_date >= CURRENT_DATE::text
            """,
            (sales_person_id,))

        commit_row = _fetchone(conn,
            """
            SELECT
                COUNT(*) AS total_commitments,
                COUNT(CASE WHEN status = 'CONVERTED' THEN 1 END) AS converted,
                COUNT(CASE WHEN status = 'PENDING' THEN 1 END) AS pending
            FROM commitments
            WHERE sales_person_id = %s AND created_at >= %s
            """,
            (sales_person_id, month_start))

        sales = float(sales_row["sales_amount"] or 0)
        target = float(target_row["sales_target"] or 1)
        achievement = min(100, (sales / target * 100)) if target > 0 else 0

        total_dealers = int(total_dealers_row["total"] or 1)
        visited = int(visit_row["visited_this_month"] or 0)
        coverage = min(100, visited / total_dealers * 100) if total_dealers > 0 else 0

        return {
            "success": True,
            "sales_person_id": sales_person_id,
            "period": now.strftime("%B %Y"),
            "sales": {
                "amount": sales,
                "target": target,
                "achievement_pct": round(achievement, 1),
                "order_count": int(sales_row["order_count"] or 0),
            },
            "collections": {"collected": float(collection_row["collected"] or 0)},
            "visits": {
                "visited_this_month": visited,
                "total_dealers": total_dealers,
                "coverage_pct": round(coverage, 1),
            },
            "commitments": {
                "total": int(commit_row["total_commitments"] or 0),
                "converted": int(commit_row["converted"] or 0),
                "pending": int(commit_row["pending"] or 0),
            },
            "pending_followups": int(followup_row["pending"] or 0),
        }
    finally:
        conn.close()
