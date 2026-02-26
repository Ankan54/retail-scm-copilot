"""
Validate the scm-dashboard-api Lambda and its API Gateway endpoints.

Tests two ways:
  1. Direct Lambda invocation (bypasses API Gateway, tests SQL/logic)
  2. HTTP calls via the API Gateway URL (end-to-end)

Usage:
    .venv/Scripts/python scripts/validate_dashboard_api.py
    .venv/Scripts/python scripts/validate_dashboard_api.py --lambda-only
    .venv/Scripts/python scripts/validate_dashboard_api.py --http-only
"""
import sys
import json
import argparse
import urllib.request
import urllib.error
from datetime import datetime

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import boto3

LAMBDA_NAME = "scm-dashboard-api"
API_GW_URL  = "https://jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod"
REGION      = "us-east-1"

SECTION = "=" * 64

# ── Expected response shape for each endpoint ────────────────────────────────
ENDPOINT_CHECKS = [
    {
        "path": "/api/metrics",
        "desc": "KPI metrics",
        "required_keys": ["revenue", "collections", "active_dealers", "at_risk",
                          "visited_30d", "pipeline_count", "pipeline_value",
                          "monthly_target", "target_pct"],
        "type": dict,
    },
    {
        "path": "/api/dealers",
        "desc": "Dealer list",
        "required_keys": ["id", "name", "health", "revenue", "lat", "lng"],
        "type": list,
    },
    {
        "path": "/api/revenue-chart",
        "desc": "Revenue chart data",
        "required_keys": ["month", "revenue", "collections", "target"],
        "type": list,
    },
    {
        "path": "/api/commitment-pipeline",
        "desc": "Commitment pipeline",
        "required_keys": ["status", "cnt", "value", "color"],
        "type": list,
    },
    {
        "path": "/api/sales-team",
        "desc": "Sales team performance",
        "required_keys": ["name", "target", "achieved", "conversion"],
        "type": list,
    },
    {
        "path": "/api/recent-activity",
        "desc": "Recent activity feed",
        "required_keys": ["type", "text", "detail", "time"],
        "type": list,
    },
    {
        "path": "/api/weekly-pipeline",
        "desc": "Weekly pipeline",
        "required_keys": ["week", "new", "confirmed", "fulfilled", "overdue"],
        "type": list,
    },
]


def _check_body(body, check):
    """Return (ok, message) after validating response body."""
    if not isinstance(body, check["type"]):
        return False, f"Expected {check['type'].__name__}, got {type(body).__name__}"

    sample = body[0] if isinstance(body, list) else body
    if not sample and isinstance(body, list):
        return True, "OK (empty list — no data in DB for this period)"

    missing = [k for k in check["required_keys"] if k not in sample]
    if missing:
        return False, f"Missing keys: {missing}"

    return True, "OK"


# ── 1. Direct Lambda invocation ───────────────────────────────────────────────

def invoke_lambda(path):
    client = boto3.client("lambda", region_name=REGION)
    payload = {
        "httpMethod": "GET",
        "path": path,
        "queryStringParameters": None,
        "requestContext": {},
    }
    resp = client.invoke(
        FunctionName=LAMBDA_NAME,
        Payload=json.dumps(payload).encode(),
    )
    result = json.loads(resp["Payload"].read())

    if "errorMessage" in result:
        return None, result["errorMessage"]

    status = result.get("statusCode", 500)
    body_raw = result.get("body", "{}")
    try:
        body = json.loads(body_raw)
    except Exception:
        return None, f"Invalid JSON body: {body_raw[:200]}"

    if status != 200:
        return None, f"HTTP {status}: {body}"

    return body, None


def test_lambda_direct():
    print(f"\n{SECTION}")
    print(f"1. DIRECT LAMBDA INVOCATION  ({LAMBDA_NAME})")
    print(SECTION)

    all_ok = True
    for check in ENDPOINT_CHECKS:
        body, err = invoke_lambda(check["path"])
        if err:
            print(f"  [FAIL] {check['path']:<30s}  {check['desc']}")
            print(f"         Error: {err}")
            all_ok = False
            continue

        ok, msg = _check_body(body, check)
        count = f"({len(body)} items)" if isinstance(body, list) else ""
        if ok:
            print(f"  [OK]   {check['path']:<30s}  {check['desc']}  {count}")
            if isinstance(body, dict):
                # Print a sample of scalar values
                sample = {k: v for k, v in body.items() if not isinstance(v, (dict, list))}
                print(f"         Sample: {json.dumps(sample, default=str)[:120]}")
            elif body:
                print(f"         Sample: {json.dumps(body[0], default=str)[:120]}")
        else:
            print(f"  [FAIL] {check['path']:<30s}  {check['desc']}")
            print(f"         {msg}")
            all_ok = False

    return all_ok


# ── 2. HTTP via API Gateway ───────────────────────────────────────────────────

def http_get(url, timeout=15):
    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode())
            return body, resp.status, None
    except urllib.error.HTTPError as e:
        return None, e.code, str(e)
    except Exception as e:
        return None, None, str(e)


def test_http_endpoints():
    print(f"\n{SECTION}")
    print(f"2. HTTP VIA API GATEWAY")
    print(f"   Base URL: {API_GW_URL}")
    print(SECTION)

    all_ok = True
    for check in ENDPOINT_CHECKS:
        url = API_GW_URL + check["path"]
        body, status, err = http_get(url)

        if err or status != 200:
            print(f"  [FAIL] {check['path']:<30s}  {check['desc']}")
            print(f"         HTTP {status}: {err or body}")
            all_ok = False
            continue

        ok, msg = _check_body(body, check)
        count = f"({len(body)} items)" if isinstance(body, list) else ""
        if ok:
            print(f"  [OK]   {check['path']:<30s}  {check['desc']}  {count}")
        else:
            print(f"  [FAIL] {check['path']:<30s}  {check['desc']}")
            print(f"         {msg}")
            all_ok = False

    return all_ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Validate scm-dashboard-api")
    parser.add_argument("--lambda-only", action="store_true")
    parser.add_argument("--http-only",   action="store_true")
    args = parser.parse_args()

    print(f"\nDashboard API Validation — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    run_lambda = not args.http_only
    run_http   = not args.lambda_only

    ok1 = test_lambda_direct() if run_lambda else True
    ok2 = test_http_endpoints() if run_http   else True

    print(f"\n{SECTION}")
    if ok1 and ok2:
        print("RESULT: ALL CHECKS PASSED ✅")
    else:
        print("RESULT: SOME CHECKS FAILED ❌  — review output above")
    print(SECTION)
    sys.exit(0 if (ok1 and ok2) else 1)


if __name__ == "__main__":
    main()
