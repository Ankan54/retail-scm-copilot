"""
Train a simple demand forecast model per product.

Algorithm: Multiplicative Seasonal Decomposition with Linear Trend
  1. Aggregate weekly demand (quantity_ordered) by month for each product
  2. Compute monthly seasonal indices (month_avg / overall_avg)
  3. Deseasonalize the weekly series
  4. Fit a linear trend on deseasonalized data
  5. Store: { product_code: { level, trend, seasonal[1..12], avg_weekly } }

The pickle is < 2KB, needs zero ML libraries on Lambda.
To plug in your own model: replace this script, regenerate the pickle,
redeploy the forecast Lambda.

Usage:
    python scripts/train_forecast_model.py
"""
import csv
import pickle
import os
from collections import defaultdict
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "synthetic")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "lambdas", "forecast")
OUTPUT_PATH = os.path.join(OUTPUT_DIR, "forecast_model.pkl")


def load_weekly_data():
    """Load weekly_sales_actuals.csv, return list of dicts."""
    path = os.path.join(DATA_DIR, "weekly_sales_actuals.csv")
    rows = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for r in reader:
            qty = int(r["quantity_ordered"])
            if qty == 0:
                continue  # skip zero-demand tail
            rows.append({
                "week_start": r["week_start"],
                "month": int(r["month"]),
                "year": int(r["year"]),
                "product_code": r["product_code"],
                "product_id": r["product_id"],
                "quantity_ordered": qty,
                "is_festival": r["is_festival_week"] == "1",
            })
    return rows


def train_model(rows):
    """
    Build per-product forecast parameters using multiplicative
    seasonal decomposition + linear trend.
    """
    # Group by product
    by_product = defaultdict(list)
    for r in rows:
        by_product[r["product_code"]].append(r)

    model = {}
    for product_code, product_rows in by_product.items():
        # Sort by time
        product_rows.sort(key=lambda x: x["week_start"])

        product_id = product_rows[0]["product_id"]
        weekly_qty = [r["quantity_ordered"] for r in product_rows]
        n = len(weekly_qty)

        # Overall average weekly demand
        avg_weekly = sum(weekly_qty) / n

        # --- Monthly seasonal indices (multiplicative) ---
        month_totals = defaultdict(list)
        for r in product_rows:
            month_totals[r["month"]].append(r["quantity_ordered"])

        seasonal = {}
        for m in range(1, 13):
            if m in month_totals:
                month_avg = sum(month_totals[m]) / len(month_totals[m])
                seasonal[m] = month_avg / avg_weekly if avg_weekly > 0 else 1.0
            else:
                seasonal[m] = 1.0

        # --- Deseasonalize and fit linear trend ---
        deseasoned = []
        for i, r in enumerate(product_rows):
            s = seasonal.get(r["month"], 1.0)
            deseasoned.append(r["quantity_ordered"] / s if s > 0 else r["quantity_ordered"])

        # Simple linear regression: y = a + b*x where x = week index
        x_mean = (n - 1) / 2.0
        y_mean = sum(deseasoned) / n

        numerator = sum((i - x_mean) * (deseasoned[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        trend = numerator / denominator if denominator > 0 else 0.0
        level = y_mean - trend * x_mean  # intercept at week 0

        # Current level = value at last observed week
        current_level = level + trend * (n - 1)

        # --- Festival boost factor ---
        festival_qtys = [r["quantity_ordered"] for r in product_rows if r["is_festival"]]
        non_festival_qtys = [r["quantity_ordered"] for r in product_rows if not r["is_festival"]]
        festival_boost = 1.0
        if festival_qtys and non_festival_qtys:
            fest_avg = sum(festival_qtys) / len(festival_qtys)
            non_fest_avg = sum(non_festival_qtys) / len(non_festival_qtys)
            if non_fest_avg > 0:
                festival_boost = fest_avg / non_fest_avg

        model[product_code] = {
            "product_id": product_id,
            "level": round(current_level, 2),
            "trend_per_week": round(trend, 4),
            "seasonal": {m: round(v, 4) for m, v in seasonal.items()},
            "avg_weekly": round(avg_weekly, 2),
            "festival_boost": round(festival_boost, 4),
            "n_weeks_trained": n,
            "last_week": product_rows[-1]["week_start"],
        }

    return model


def main():
    print("Loading weekly sales data...")
    rows = load_weekly_data()
    print(f"  {len(rows)} non-zero weekly records across {len(set(r['product_code'] for r in rows))} products")

    print("Training forecast model...")
    model = train_model(rows)

    for code, params in model.items():
        print(f"\n  {code}:")
        print(f"    Level (current):    {params['level']:.1f} units/week")
        print(f"    Trend per week:     {params['trend_per_week']:+.2f} units")
        print(f"    Avg weekly demand:  {params['avg_weekly']:.1f} units")
        print(f"    Festival boost:     {params['festival_boost']:.2f}x")
        print(f"    Seasonal indices:   ", end="")
        months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        for m in range(1, 13):
            print(f"{months[m-1]}={params['seasonal'][m]:.2f}", end=" ")
        print()

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_PATH, "wb") as f:
        pickle.dump(model, f, protocol=2)  # protocol 2 for max compatibility

    size = os.path.getsize(OUTPUT_PATH)
    print(f"\nModel saved to {OUTPUT_PATH} ({size} bytes)")
    print("Done.")


if __name__ == "__main__":
    main()
