"""
Demand Forecast Lambda — Pluggable forecasting model for Bedrock agents.

This Lambda loads a pre-trained forecast model (pickle) and generates
weekly demand predictions per product. The model uses multiplicative
seasonal decomposition with linear trend.

** HACKATHON PITCH **
Any MSME can swap in their own forecasting model — ML, statistical,
ERP-based, or even a simple heuristic — by:
  1. Replacing forecast_model.pkl with their own model output
  2. Updating the predict() function below
  3. Redeploying this single Lambda
The Bedrock agent automatically uses whatever model is plugged in.

Endpoints:
  - Bedrock Agent tool: get_demand_forecast(product_code, horizon_weeks)
  - API Gateway GET:    /api/forecast?product=CLN-500G&weeks=8
"""
import json
import pickle
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Load model at cold-start (outside handler for reuse across invocations)
MODEL_PATH = os.path.join(os.path.dirname(__file__), "forecast_model.pkl")
MODEL = {}

try:
    with open(MODEL_PATH, "rb") as f:
        MODEL = pickle.load(f)
    logger.info(f"Forecast model loaded: {list(MODEL.keys())}")
except Exception as e:
    logger.error(f"Failed to load forecast model: {e}")


# Indian festival months (approximate)
FESTIVAL_MONTHS = {3, 10}  # March (Holi), October (Diwali)


def predict(product_code, horizon_weeks=8, start_date=None):
    """
    Generate weekly demand forecast for a product.

    This is the function to replace with your own model.
    Input:  product_code (str), horizon_weeks (int)
    Output: list of { week_start, week_end, forecast_qty, month, is_festival }
    """
    if product_code not in MODEL:
        return {"error": f"Unknown product: {product_code}. Available: {list(MODEL.keys())}"}

    params = MODEL[product_code]
    level = params["level"]
    trend = params["trend_per_week"]
    seasonal = params["seasonal"]
    festival_boost = params.get("festival_boost", 1.0)

    if start_date is None:
        start_date = datetime.now()

    # Find next Monday
    days_until_monday = (7 - start_date.weekday()) % 7
    if days_until_monday == 0:
        days_until_monday = 7
    week_start = start_date + timedelta(days=days_until_monday)

    forecasts = []
    for i in range(horizon_weeks):
        ws = week_start + timedelta(weeks=i)
        we = ws + timedelta(days=6)
        month = ws.month

        # Base forecast: current level + trend * weeks ahead
        base = level + trend * (i + 1)

        # Apply seasonal factor
        s = seasonal.get(month, 1.0)
        forecast = base * s

        # Apply festival boost if applicable
        is_festival = month in FESTIVAL_MONTHS
        if is_festival:
            forecast *= festival_boost

        forecast = max(0, round(forecast))

        forecasts.append({
            "week_start": ws.strftime("%Y-%m-%d"),
            "week_end": we.strftime("%Y-%m-%d"),
            "forecast_qty": forecast,
            "month": month,
            "is_festival": is_festival,
        })

    return forecasts


def get_demand_forecast(product_code=None, horizon_weeks=8):
    """
    Called by the Bedrock agent.
    If product_code is 'all' or None, returns forecast for all products.
    """
    horizon_weeks = min(int(horizon_weeks), 26)  # cap at 6 months

    if product_code and product_code.lower() != "all":
        product_code = product_code.upper()
        forecasts = predict(product_code, horizon_weeks)
        if isinstance(forecasts, dict) and "error" in forecasts:
            return forecasts
        # Compute summary
        total_qty = sum(f["forecast_qty"] for f in forecasts)
        return {
            "product_code": product_code,
            "product_id": MODEL.get(product_code, {}).get("product_id", ""),
            "horizon_weeks": horizon_weeks,
            "total_forecast_qty": total_qty,
            "avg_weekly_forecast": round(total_qty / horizon_weeks) if horizon_weeks > 0 else 0,
            "weekly_forecast": forecasts,
            "model_info": {
                "type": "Seasonal Decomposition + Linear Trend",
                "training_weeks": MODEL.get(product_code, {}).get("n_weeks_trained", 0),
                "last_training_data": MODEL.get(product_code, {}).get("last_week", ""),
            },
        }
    else:
        # All products
        results = {}
        for code in MODEL:
            forecasts = predict(code, horizon_weeks)
            total_qty = sum(f["forecast_qty"] for f in forecasts)
            results[code] = {
                "product_id": MODEL[code].get("product_id", ""),
                "total_forecast_qty": total_qty,
                "avg_weekly_forecast": round(total_qty / horizon_weeks) if horizon_weeks > 0 else 0,
                "weekly_forecast": forecasts,
            }
        return {
            "horizon_weeks": horizon_weeks,
            "products": results,
            "model_info": {
                "type": "Seasonal Decomposition + Linear Trend",
                "note": "Replace this Lambda to plug in your own forecasting model",
            },
        }


def _serialize(obj):
    if isinstance(obj, (datetime,)):
        return obj.isoformat()
    return str(obj)


def lambda_handler(event, context):
    """
    Dual-mode handler:
      1. Bedrock Agent action group (has 'function' key)
      2. API Gateway GET /api/forecast (has 'path' key)
    """
    logger.info(f"Event: {json.dumps(event, default=str)}")

    # --- Mode 1: Bedrock Agent ---
    if "function" in event:
        import sys
        sys.path.insert(0, "/opt/python")
        sys.path.insert(0, "/var/task")
        from shared.db_utils import bedrock_response

        action_group = event.get("actionGroup", "forecast")
        function = event["function"]
        params = {p["name"]: p["value"] for p in event.get("parameters", [])}

        try:
            if function == "get_demand_forecast":
                result = get_demand_forecast(
                    product_code=params.get("product_code", "all"),
                    horizon_weeks=int(params.get("horizon_weeks", 8)),
                )
            else:
                result = {"error": f"Unknown function: {function}"}
        except Exception as e:
            logger.exception(f"Error in {function}")
            result = {"error": str(e)}

        return bedrock_response(action_group, function, result)

    # --- Mode 2: API Gateway / Dashboard ---
    path = event.get("path", event.get("rawPath", ""))
    method = event.get("httpMethod", "GET")

    if method == "OPTIONS":
        return _resp(200, {})

    query = event.get("queryStringParameters") or {}
    product_code = query.get("product", "all")
    horizon_weeks = int(query.get("weeks", 8))

    try:
        data = get_demand_forecast(product_code, horizon_weeks)
        return _resp(200, data)
    except Exception as e:
        logger.exception("Forecast API error")
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
