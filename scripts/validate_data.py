#!/usr/bin/env python3
"""Validate generated synthetic data for referential integrity and business rules."""
import csv, os
from collections import Counter

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'synthetic')

def load(name):
    with open(os.path.join(D, f'{name}.csv'), encoding='utf-8') as f:
        return list(csv.DictReader(f))

print("=== Validation Report ===\n")

# Load key tables
territories = {r['territory_id']: r for r in load('territories')}
sales_persons = {r['sales_person_id']: r for r in load('sales_persons')}
products = {r['product_id']: r for r in load('products')}
prod_by_code = {r['product_code']: r['product_id'] for r in products.values()}
dealers = {r['dealer_id']: r for r in load('dealers')}
orders = {r['order_id']: r for r in load('orders')}
invoices = {r['invoice_id']: r for r in load('invoices')}
visits = {r['visit_id']: r for r in load('visits')}
commitments = {r['commitment_id']: r for r in load('commitments')}
routes = {r['route_id']: r for r in load('delivery_routes')}

errors = 0

# 1. Referential Integrity
print("--- Referential Integrity ---")

bad = sum(1 for d in dealers.values() if d['territory_id'] not in territories)
print(f"  Dealers->territories: {bad} errors"); errors += bad

bad = sum(1 for d in dealers.values() if d['sales_person_id'] not in sales_persons)
print(f"  Dealers->sales_persons: {bad} errors"); errors += bad

bad = sum(1 for o in orders.values() if o['dealer_id'] not in dealers)
print(f"  Orders->dealers: {bad} errors"); errors += bad

order_items = load('order_items')
bad = sum(1 for oi in order_items if oi['order_id'] not in orders)
print(f"  OrderItems->orders: {bad} errors"); errors += bad

bad = sum(1 for oi in order_items if oi['product_id'] not in products)
print(f"  OrderItems->products: {bad} errors"); errors += bad

bad = sum(1 for inv in invoices.values() if inv['order_id'] not in orders)
print(f"  Invoices->orders: {bad} errors"); errors += bad

payments = load('payments')
bad = sum(1 for p in payments if p['invoice_id'] and p['invoice_id'] not in invoices)
print(f"  Payments->invoices: {bad} errors"); errors += bad

bad = sum(1 for c in commitments.values() if c['visit_id'] not in visits)
print(f"  Commitments->visits: {bad} errors"); errors += bad

route_stops = load('route_stops')
bad = sum(1 for rs in route_stops if rs['route_id'] not in routes)
print(f"  RouteStops->routes: {bad} errors"); errors += bad

# Weekly sales actuals -> products
wsa = load('weekly_sales_actuals')
bad = sum(1 for w in wsa if w['product_id'] not in products)
print(f"  WeeklySalesActuals->products: {bad} errors"); errors += bad

# 2. Primary Key Uniqueness
print("\n--- PK Uniqueness ---")
for name, key in [('dealers','dealer_id'),('orders','order_id'),('invoices','invoice_id'),
                   ('visits','visit_id'),('products','product_id')]:
    data = load(name)
    ids = [r[key] for r in data]
    dups = len(ids) - len(set(ids))
    print(f"  {name}.{key}: {dups} duplicates"); errors += dups

for name, key in [('dealers','dealer_code'),('sales_persons','employee_code'),('products','product_code')]:
    data = load(name)
    codes = [r[key] for r in data]
    dups = len(codes) - len(set(codes))
    print(f"  {name}.{key}: {dups} duplicates"); errors += dups

# 3. Business Rules
print("\n--- Business Rules ---")

cats = Counter(d['category'] for d in dealers.values())
print(f"  Dealer categories: A={cats.get('A',0)}, B={cats.get('B',0)}, C={cats.get('C',0)}")

# Weekly sales actuals: 156 records = 52 weeks x 3 products
print(f"  Weekly sales actuals: {len(wsa)} records (expected 156)")
if len(wsa) != 156:
    print(f"    ERROR: expected 156"); errors += 1

# Check all 3 product codes present
wsa_codes = set(w['product_code'] for w in wsa)
print(f"  WSA product codes: {sorted(wsa_codes)}")
if wsa_codes != {'CLN-500G', 'CLN-1KG', 'CLN-2KG'}:
    print(f"    ERROR: missing product codes"); errors += 1

# 1kg training data has 52 rows
wsa_1kg = [w for w in wsa if w['product_code'] == 'CLN-1KG']
print(f"  WSA 1kg rows (for model training): {len(wsa_1kg)}")

# Festival weeks flagged
festival_weeks = sum(1 for w in wsa if w['is_festival_week'] == '1')
print(f"  Festival week flags: {festival_weeks}")

overdue = sum(1 for inv in invoices.values() if inv['status'] == 'OVERDUE')
print(f"  Overdue invoices: {overdue}")

pending = sum(1 for c in commitments.values() if c['status'] == 'PENDING')
print(f"  Pending commitments: {pending}")

health = load('dealer_health_scores')
atrisk = len(set(h['dealer_id'] for h in health if h['health_status'] in ('AT_RISK','CRITICAL')))
print(f"  Dealers ever AT_RISK/CRITICAL: {atrisk}")

di = load('dealer_inventory')
low = sum(1 for x in di if int(x['current_stock']) < int(x['reorder_point']))
print(f"  Low stock inventory records: {low}")

lats = [float(d['latitude']) for d in dealers.values()]
lngs = [float(d['longitude']) for d in dealers.values()]
lat_ok = all(28.40 <= l <= 28.85 for l in lats)
lng_ok = all(76.85 <= l <= 77.35 for l in lngs)
print(f"  Lat bounds OK: {lat_ok}  Lng bounds OK: {lng_ok}")
if not lat_ok: errors += 1
if not lng_ok: errors += 1

# Record counts summary
print("\n--- Record Counts ---")
tables = ['territories','sales_persons','territory_assignments','product_categories',
          'hsn_codes','products','warehouses','dealers','dealer_inventory','inventory',
          'incoming_stock','production_capacity','production_schedule','visits','commitments',
          'orders','order_items','order_splits','invoices','payments','issues','vehicles',
          'delivery_routes','route_stops','alerts','sales_targets','dealer_health_scores',
          'weekly_sales_actuals','consumption_config','system_settings']
total = 0
for t in tables:
    n = len(load(t))
    total += n
    print(f"  {t:35s} {n:>6d}")
print(f"  {'TOTAL':35s} {total:>6d}")

print(f"\n=== TOTAL ERRORS: {errors} ===")
if errors == 0:
    print("ALL CHECKS PASSED!")
