#!/usr/bin/env python3
"""Synthetic Data Generator for SupplyChain Copilot - Part 1: Core tables"""
import csv, os, random, uuid, math
from datetime import datetime, timedelta, date, time
from pathlib import Path

random.seed(42)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Helpers ────────────────────────────────────────────────────────
def genuuid(): return str(uuid.uuid4())
def write_csv(name, rows, fieldnames):
    p = OUTPUT_DIR / f"{name}.csv"
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(rows)
    print(f"  {name}.csv  →  {len(rows)} rows")
    return rows

def delhi_mobile():
    pfx = random.choice(['9810','9811','9899','9958','8800','8801','7838','7042'])
    return pfx + ''.join(str(random.randint(0,9)) for _ in range(6))

def rand_dt(start, end):
    delta = (end - start).total_seconds()
    return start + timedelta(seconds=random.randint(0, int(delta)))

def rand_date(start, end):
    return rand_dt(datetime.combine(start,time.min), datetime.combine(end,time.min)).date()

def fmt_dt(dt):
    if dt is None: return ""
    if isinstance(dt, date) and not isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def fmt_val(v):
    if v is None: return ""
    return v

MONTHLY_MULT = {1:0.80,2:0.90,3:1.20,4:1.00,5:1.00,6:0.85,7:0.80,8:0.90,9:1.00,10:1.35,11:1.20,12:1.00}
DOW_MULT = {0:1.00,1:1.10,2:1.00,3:1.10,4:0.90,5:0.70,6:0.20}

DATA_START = date(2024,3,1)
DATA_END   = date(2025,2,24)
CURRENT    = date(2025,2,24)

# ─── ID Registry ───────────────────────────────────────────────────
R = {}  # global registry

# ═══════════ TABLE 1: territories ═══════════
def gen_territories():
    names = ["North Delhi","South Delhi","East Delhi","West Delhi","Central Delhi"]
    rows = []
    R['territories'] = {}
    for n in names:
        tid = genuuid()
        R['territories'][n] = tid
        rows.append(dict(territory_id=tid, name=n, region="Delhi NCR", state="Delhi",
                         parent_territory_id="", is_active=1,
                         created_at="2024-01-01 00:00:00", updated_at="2024-01-01 00:00:00"))
    return write_csv("territories", rows,
        ["territory_id","name","region","state","parent_territory_id","is_active","created_at","updated_at"])

# ═══════════ TABLE 2: sales_persons ═══════════
def gen_sales_persons():
    R['sales_persons'] = {}
    mgr_id = genuuid()
    reps_info = [
        ("EMP001","Rajesh Kumar","rajesh.kumar@cleanmax.in","9810234567","MANAGER",None,"2020-01-15"),
        ("EMP002","Amit Sharma","amit.sharma@cleanmax.in","9811345678","REP",mgr_id,"2021-03-01"),
        ("EMP003","Sunil Verma","sunil.verma@cleanmax.in","9899456789","REP",mgr_id,"2022-01-15"),
        ("EMP004","Deepak Singh","deepak.singh@cleanmax.in","8800567890","REP",mgr_id,"2022-08-01"),
        ("EMP005","Vikram Gupta","vikram.gupta@cleanmax.in","7838678901","REP",mgr_id,"2023-06-01"),
    ]
    rows = []
    for i,(code,name,email,phone,role,mid,doj) in enumerate(reps_info):
        sid = mgr_id if code=="EMP001" else genuuid()
        R['sales_persons'][code] = sid
        rows.append(dict(
            sales_person_id=sid, employee_code=code, name=name, email=email, phone=phone,
            role=role, manager_id=fmt_val(mid), telegram_user_id=f"TG_10000{i+1}",
            telegram_chat_id=f"CHAT_10000{i+1}", is_active=1, date_of_joining=doj,
            created_at=f"{doj} 00:00:00", updated_at="2024-06-01 00:00:00"))
    R['manager_id'] = mgr_id
    return write_csv("sales_persons", rows,
        ["sales_person_id","employee_code","name","email","phone","role","manager_id",
         "telegram_user_id","telegram_chat_id","is_active","date_of_joining","created_at","updated_at"])

# ═══════════ TABLE 3: territory_assignments ═══════════
def gen_territory_assignments():
    assignments = [
        ("EMP002","North Delhi",1), ("EMP003","South Delhi",1),
        ("EMP004","East Delhi",1),  ("EMP005","West Delhi",1),
        ("EMP005","Central Delhi",0),
    ]
    rows = []
    R['territory_assignments'] = {}
    for code, tname, pri in assignments:
        aid = genuuid()
        rows.append(dict(assignment_id=aid, sales_person_id=R['sales_persons'][code],
                         territory_id=R['territories'][tname], is_primary=pri,
                         assigned_date="2024-01-01", end_date=""))
        R['territory_assignments'][tname] = R['sales_persons'][code]  # territory→rep
    return write_csv("territory_assignments", rows,
        ["assignment_id","sales_person_id","territory_id","is_primary","assigned_date","end_date"])

# ═══════════ TABLE 4: product_categories ═══════════
def gen_product_categories():
    cid = genuuid()
    R['category_id'] = cid
    rows = [dict(category_id=cid, name="Detergents", parent_category_id="",
                 description="Laundry detergent powders for household use",
                 is_active=1, created_at="2024-01-01 00:00:00")]
    return write_csv("product_categories", rows,
        ["category_id","name","parent_category_id","description","is_active","created_at"])

# ═══════════ TABLE 5: hsn_codes ═══════════
def gen_hsn_codes():
    rows = [dict(hsn_code="3402",
                 description="Organic surface-active agents; washing preparations",
                 gst_rate=18.0, cgst_rate=9.0, sgst_rate=9.0, igst_rate=18.0, cess_rate=0.0,
                 effective_from="2017-07-01", effective_to="", created_at="2024-01-01 00:00:00")]
    return write_csv("hsn_codes", rows,
        ["hsn_code","description","gst_rate","cgst_rate","sgst_rate","igst_rate","cess_rate",
         "effective_from","effective_to","created_at"])

# ═══════════ TABLE 6: products ═══════════
def gen_products():
    R['products'] = {}
    specs = [
        ("CLN-500G","CleanMax Detergent 500g","CleanMax 500g","Premium detergent powder for daily laundry",
         45.00,40.00,36.00,34.00,24,12,200,50,"2020-01-01"),
        ("CLN-1KG","CleanMax Detergent 1kg","CleanMax 1kg","Premium detergent powder - Family pack",
         85.00,76.00,68.00,64.00,12,6,150,40,"2020-01-01"),
        ("CLN-2KG","CleanMax Detergent 2kg","CleanMax 2kg","Premium detergent powder - Value pack",
         160.00,144.00,128.00,120.00,6,3,100,30,"2021-06-01"),
    ]
    rows = []
    for code,name,short,desc,mrp,up,dp,distp,upc,moq,reord,safe,launch in specs:
        pid = genuuid()
        R['products'][code] = pid
        rows.append(dict(
            product_id=pid, product_code=code, name=name, short_name=short, description=desc,
            category_id=R['category_id'], brand="CleanMax", hsn_code="3402",
            mrp=mrp, unit_price=up, dealer_price=dp, distributor_price=distp,
            unit_of_measure="PCS", units_per_case=upc, min_order_qty=moq,
            reorder_level=reord, safety_stock=safe, lead_time_days=1, is_manufactured=1,
            status="ACTIVE", launch_date=launch, discontinue_date="",
            created_at=f"{launch} 00:00:00", updated_at="2024-01-01 00:00:00"))
    R['PRIMARY_FORECAST_PRODUCT_ID'] = R['products']['CLN-1KG']
    return write_csv("products", rows,
        ["product_id","product_code","name","short_name","description","category_id","brand","hsn_code",
         "mrp","unit_price","dealer_price","distributor_price","unit_of_measure","units_per_case",
         "min_order_qty","reorder_level","safety_stock","lead_time_days","is_manufactured","status",
         "launch_date","discontinue_date","created_at","updated_at"])

# ═══════════ TABLE 7: warehouses ═══════════
def gen_warehouses():
    wid = genuuid()
    R['warehouse_id'] = wid
    rows = [dict(warehouse_id=wid, name="CleanMax Godown", code="WH001",
                 address="Plot 45, Industrial Area, Okhla Phase 2", city="New Delhi",
                 state="Delhi", pincode="110020", latitude=28.5355, longitude=77.2685,
                 is_primary=1, is_active=1, created_at="2020-01-01 00:00:00")]
    return write_csv("warehouses", rows,
        ["warehouse_id","name","code","address","city","state","pincode","latitude","longitude",
         "is_primary","is_active","created_at"])

# ═══════════ TABLE 8: dealers ═══════════
def gen_dealers():
    AREAS = {
        "North Delhi": {
            "names": ["Sharma General Store","Gupta Kirana","Verma Traders","Aggarwal Stores",
                      "Singh Provision Store","Bansal Grocers","Jain Supermart","Kapoor Store","Malhotra Kirana"],
            "contacts": ["Ramesh Sharma","Suresh Gupta","Mahesh Verma","Pankaj Aggarwal",
                         "Harpal Singh","Rohit Bansal","Pradeep Jain","Anil Kapoor","Sanjay Malhotra"],
            "localities": ["Rohini Sec 7","Pitampura","Model Town","Shalimar Bagh","Ashok Vihar",
                           "Rohini Sec 3","Pitampura Main Market","Model Town Part 2","Shalimar Bagh Ring Rd"],
            "pincodes": ["110085","110034","110033","110088","110052","110085","110034","110033","110088"],
            "lat": (28.70,28.75), "lng": (77.10,77.15),
            "cat_dist": [0,1,0,1,0,0,0,1,0]  # 1=A → 2A, rest B/C
        },
        "South Delhi": {
            "names": ["Krishna Stores","Lakshmi General Store","Sai Kirana","Ram Traders",
                      "Sundar Provision","Balaji Store","Ganesh Grocers","Shiv Kirana","Durga Stores"],
            "contacts": ["Gopal Krishna","Venkat Lakshmi","Sai Prakash","Ram Naresh",
                         "Sundar Lal","Balaji Rao","Ganesh Iyer","Shiv Kumar","Durga Prasad"],
            "localities": ["Saket","Malviya Nagar","Greater Kailash I","Lajpat Nagar",
                           "Kalkaji","Saket Main Market","Malviya Nagar Block B","GK II","Lajpat Nagar II"],
            "pincodes": ["110017","110017","110048","110024","110019","110017","110017","110048","110024"],
            "lat": (28.52,28.57), "lng": (77.20,77.26),
            "cat_dist": [1,0,0,0,0,0,0,0,0]  # 1A
        },
        "East Delhi": {
            "names": ["Yadav Stores","Pandey Kirana","Dubey General Store","Tiwari Traders",
                      "Mishra Provision","Kumar Store","Sahu Grocers","Prasad Kirana","Maurya Stores"],
            "contacts": ["Rajendra Yadav","Ashok Pandey","Vinod Dubey","Manoj Tiwari",
                         "Rakesh Mishra","Ajay Kumar","Dinesh Sahu","Mohan Prasad","Santosh Maurya"],
            "localities": ["Laxmi Nagar","Preet Vihar","Mayur Vihar Phase I","Shakarpur",
                           "Patparganj","Laxmi Nagar Main","Preet Vihar Market","Mayur Vihar Phase II","Shakarpur Main"],
            "pincodes": ["110092","110092","110091","110032","110092","110092","110092","110091","110032"],
            "lat": (28.62,28.67), "lng": (77.28,77.32),
            "cat_dist": [1,0,0,0,0,0,0,0,0]  # 1A
        },
        "West Delhi": {
            "names": ["Chaudhary Kirana","Dahiya Stores","Tanwar General Store","Malik Traders",
                      "Rana Provision","Nagar Store","Hooda Grocers","Sangwan Kirana","Dhillon Stores"],
            "contacts": ["Naresh Chaudhary","Surender Dahiya","Praveen Tanwar","Irfan Malik",
                         "Vijay Rana","Suresh Nagar","Satish Hooda","Jagdish Sangwan","Gurpreet Dhillon"],
            "localities": ["Rajouri Garden","Janakpuri","Tilak Nagar","Uttam Nagar",
                           "Vikaspuri","Rajouri Garden Main","Janakpuri C Block","Tilak Nagar Market","Uttam Nagar East"],
            "pincodes": ["110027","110058","110018","110059","110018","110027","110058","110018","110059"],
            "lat": (28.62,28.66), "lng": (77.05,77.12),
            "cat_dist": [1,0,0,0,0,0,0,0,0]  # 1A
        },
        "Central Delhi": {
            "names": ["Old Delhi Kirana","Chandni Store","Sadar Traders","Nai Sarak Provision",
                      "Chawri Bazaar Store","Khari Baoli Grocers","Dariba Kirana","Ballimaran Store","Fatehpuri Stores"],
            "contacts": ["Mohammed Ishaq","Ravi Chandra","Naeem Ahmed","Pappu Lal",
                         "Zaheer Khan","Brijesh Goyal","Sonu Bansal","Asif Ali","Firoz Qureshi"],
            "localities": ["Karol Bagh","Paharganj","Chandni Chowk","Daryaganj",
                           "Connaught Place","Karol Bagh Main","Paharganj Market","Chandni Chowk Main","Daryaganj Main"],
            "pincodes": ["110005","110055","110006","110002","110001","110005","110055","110006","110002"],
            "lat": (28.64,28.67), "lng": (77.20,77.24),
            "cat_dist": [0,0,0,0,0,0,0,0,0]  # 0A
        },
    }
    # Category distribution:  North 2A,3B,4C | South 1A,3B,5C | East 1A,3B,5C | West 1A,3B,5C | Central 0A,3B,6C
    CAT_MAP = {
        "North Delhi":   ["A","A","B","B","B","C","C","C","C"],
        "South Delhi":   ["A","B","B","B","C","C","C","C","C"],
        "East Delhi":    ["A","B","B","B","C","C","C","C","C"],
        "West Delhi":    ["A","B","B","B","C","C","C","C","C"],
        "Central Delhi": ["B","B","B","C","C","C","C","C","C"],
    }
    CREDIT = {"A":50000,"B":25000,"C":10000}
    STATUS_POOL = ["ACTIVE"]*42 + ["INACTIVE"]*2 + ["BLOCKED"]*1
    random.shuffle(STATUS_POOL)

    R['dealers'] = {}
    R['dealer_list'] = []
    R['active_dealers'] = []
    rows = []
    dlr_idx = 0
    for tname in ["North Delhi","South Delhi","East Delhi","West Delhi","Central Delhi"]:
        area = AREAS[tname]
        cats = CAT_MAP[tname]
        rep_id = R['territory_assignments'][tname]
        tid = R['territories'][tname]
        for i in range(9):
            dlr_idx += 1
            did = genuuid()
            code = f"DLR{dlr_idx:03d}"
            cat = cats[i]
            status = STATUS_POOL[dlr_idx-1] if dlr_idx-1 < len(STATUS_POOL) else "ACTIVE"
            lat = round(random.uniform(*area['lat']),6)
            lng = round(random.uniform(*area['lng']),6)
            onboard = rand_date(date(2020,6,1), date(2024,8,1))
            has_email = random.random() < 0.2
            has_alt = random.random() < 0.3
            has_pan = random.random() < 0.3
            pmode = random.choice(["CREDIT"]*6 + ["CASH"]*4)
            cdays = random.choice([7,15])
            if status == "ACTIVE":
                lo = rand_date(CURRENT - timedelta(days=30), CURRENT)
                lv = rand_date(CURRENT - timedelta(days=14), CURRENT)
            elif status == "INACTIVE":
                lo = rand_date(CURRENT - timedelta(days=120), CURRENT - timedelta(days=60))
                lv = rand_date(CURRENT - timedelta(days=60), CURRENT - timedelta(days=30))
            else:
                lo = rand_date(CURRENT - timedelta(days=180), CURRENT - timedelta(days=90))
                lv = lo
            cfr = round(random.uniform(0.75,0.95) if cat=="A" else random.uniform(0.60,0.90),2)
            row = dict(
                dealer_id=did, dealer_code=code, name=area['names'][i], trade_name=area['names'][i],
                dealer_type="RETAILER", category=cat, contact_person=area['contacts'][i],
                contact_phone=delhi_mobile(),
                contact_email=f"{area['contacts'][i].split()[0].lower()}@gmail.com" if has_email else "",
                alternate_phone=delhi_mobile() if has_alt else "",
                address_line1=f"Shop No. {random.randint(1,120)}, {area['localities'][i]}",
                address_line2=f"Near {random.choice(['Metro Station','Bus Stop','Main Road','Temple','Park'])}" if random.random()<0.3 else "",
                city="New Delhi", district=tname, state="Delhi", pincode=area['pincodes'][i],
                latitude=lat, longitude=lng, gstin="",
                pan=f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ',k=5))}{''.join(str(random.randint(0,9)) for _ in range(4))}{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ',k=1))}" if has_pan else "",
                credit_limit=CREDIT[cat], credit_days=cdays, payment_mode=pmode,
                territory_id=tid, sales_person_id=rep_id, status=status,
                onboarding_date=fmt_dt(onboard),
                last_order_date=fmt_dt(lo), last_visit_date=fmt_dt(lv),
                commitment_fulfillment_rate=cfr, avg_days_to_fulfill=random.randint(2,7),
                created_at=fmt_dt(onboard), updated_at="2025-01-15 00:00:00")
            rows.append(row)
            R['dealers'][code] = did
            info = dict(did=did, code=code, cat=cat, status=status, territory=tname,
                        rep_id=rep_id, lat=lat, lng=lng, territory_id=tid)
            R['dealer_list'].append(info)
            if status == "ACTIVE":
                R['active_dealers'].append(info)
    return write_csv("dealers", rows,
        ["dealer_id","dealer_code","name","trade_name","dealer_type","category","contact_person",
         "contact_phone","contact_email","alternate_phone","address_line1","address_line2",
         "city","district","state","pincode","latitude","longitude","gstin","pan",
         "credit_limit","credit_days","payment_mode","territory_id","sales_person_id","status",
         "onboarding_date","last_order_date","last_visit_date","commitment_fulfillment_rate",
         "avg_days_to_fulfill","created_at","updated_at"])

# ═══════════ TABLE 9: dealer_inventory ═══════════
def gen_dealer_inventory():
    rows = []
    R['low_stock_dealers'] = []
    pids = [R['products']['CLN-500G'], R['products']['CLN-1KG'], R['products']['CLN-2KG']]
    stock_ranges = {"A":(20,100),"B":(10,50),"C":(5,25)}
    reorder = {"A":30,"B":15,"C":8}
    maxs = {"A":150,"B":75,"C":40}
    adc_ranges = {"A":(5,10),"B":(2,5),"C":(1,3)}
    dealers_2kg = random.sample(R['active_dealers'], min(25, len(R['active_dealers'])))
    d2kg_set = {d['did'] for d in dealers_2kg}
    low_count = 0
    for d in R['active_dealers']:
        prods = [0,1]  # 500g, 1kg
        if d['did'] in d2kg_set:
            prods.append(2)
        for pi in prods:
            cat = d['cat']
            cs = random.randint(*stock_ranges[cat])
            # Force some low stock for demo
            if low_count < 10 and pi == 1 and random.random() < 0.25:
                cs = random.randint(1, reorder[cat]-1)
                low_count += 1
            adc = random.randint(*adc_ranges[cat])
            dos = round(cs / max(adc,1), 1)
            lu = rand_date(date(2025,2,17), date(2025,2,24))
            rows.append(dict(
                dealer_inventory_id=genuuid(), dealer_id=d['did'], product_id=pids[pi],
                current_stock=cs, reorder_point=reorder[cat], max_stock=maxs[cat],
                avg_daily_consumption=adc, days_of_stock=dos, last_updated=fmt_dt(lu)))
            if cs < reorder[cat]:
                R['low_stock_dealers'].append(d['did'])
    return write_csv("dealer_inventory", rows,
        ["dealer_inventory_id","dealer_id","product_id","current_stock","reorder_point",
         "max_stock","avg_daily_consumption","days_of_stock","last_updated"])

# ═══════════ TABLE 10: inventory ═══════════
def gen_inventory():
    specs = [("CLN-500G",800,100),("CLN-1KG",500,80),("CLN-2KG",250,40)]
    rows = []
    for code,qoh,qr in specs:
        rows.append(dict(inventory_id=genuuid(), product_id=R['products'][code],
                         warehouse_id=R['warehouse_id'], qty_on_hand=qoh, qty_reserved=qr,
                         batch_number="BATCH-202502-001", expiry_date="",
                         last_updated="2025-02-24 08:00:00"))
    return write_csv("inventory", rows,
        ["inventory_id","product_id","warehouse_id","qty_on_hand","qty_reserved",
         "batch_number","expiry_date","last_updated"])

# ═══════════ TABLE 11: incoming_stock ═══════════
def gen_incoming_stock():
    rows = []
    prods = ["CLN-500G"]*4 + ["CLN-1KG"]*4 + ["CLN-2KG"]*2
    for i, pcode in enumerate(prods):
        is_past = i < 5
        if is_past:
            exp = rand_date(date(2025,2,10), date(2025,2,22))
        else:
            exp = rand_date(date(2025,2,25), date(2025,3,3))
        qty = random.randint(100,300)
        arq = int(qty * random.uniform(0.95,1.0)) if is_past else None
        rows.append(dict(
            incoming_stock_id=genuuid(), product_id=R['products'][pcode],
            warehouse_id=R['warehouse_id'], quantity=qty,
            expected_date=fmt_dt(exp), source_type="PRODUCTION",
            source_reference=f"PROD-2025-{i+1:03d}",
            status="RECEIVED" if is_past else "EXPECTED",
            actual_received_qty=fmt_val(arq),
            received_date=fmt_dt(exp) if is_past else "",
            created_at=fmt_dt(exp - timedelta(days=3)),
            updated_at=fmt_dt(exp) if is_past else fmt_dt(exp - timedelta(days=3))))
    return write_csv("incoming_stock", rows,
        ["incoming_stock_id","product_id","warehouse_id","quantity","expected_date","source_type",
         "source_reference","status","actual_received_qty","received_date","created_at","updated_at"])

# ═══════════ TABLE 12: production_capacity ═══════════
def gen_production_capacity():
    specs = [("CLN-500G",300,1500,6000),("CLN-1KG",150,750,3000),("CLN-2KG",75,375,1500)]
    rows = []
    for code,d,w,m in specs:
        rows.append(dict(capacity_id=genuuid(), product_id=R['products'][code],
                         daily_capacity=d, weekly_capacity=w, monthly_capacity=m,
                         effective_from="2024-01-01", effective_to="", notes="",
                         created_at="2024-01-01 00:00:00"))
    return write_csv("production_capacity", rows,
        ["capacity_id","product_id","daily_capacity","weekly_capacity","monthly_capacity",
         "effective_from","effective_to","notes","created_at"])

# ═══════════ TABLE 13: production_schedule ═══════════
def gen_production_schedule():
    rows = []
    product_pool = ["CLN-500G"]*50 + ["CLN-1KG"]*35 + ["CLN-2KG"]*15
    product_pool = product_pool + product_pool[:50]  # pad to 150
    random.shuffle(product_pool)
    cap = {"CLN-500G":200,"CLN-1KG":150,"CLN-2KG":75}
    # Generate 150 weekday dates spread over 12 months
    all_days = []
    d = DATA_START
    while d <= DATA_END:
        if d.weekday() < 6:  # Mon–Sat
            all_days.append(d)
        d += timedelta(days=1)
    sched_dates = sorted(random.sample(all_days, min(150, len(all_days))))
    for i, sd in enumerate(sched_dates):
        pcode = product_pool[i % len(product_pool)]
        pqty = random.randint(50, cap[pcode])
        is_past = sd < CURRENT
        if is_past:
            r = random.random()
            if r < 0.90: st = "COMPLETED"
            elif r < 0.95: st = "CANCELLED"
            else: st = "IN_PROGRESS"
        else:
            st = "PLANNED"
        aqty = int(pqty * random.uniform(0.90,1.05)) if st=="COMPLETED" else (None if st in ("PLANNED","CANCELLED") else pqty)
        rows.append(dict(
            schedule_id=genuuid(), product_id=R['products'][pcode],
            planned_date=fmt_dt(sd), planned_qty=pqty,
            actual_qty=fmt_val(aqty), status=st,
            created_at=fmt_dt(sd - timedelta(days=7)),
            updated_at=fmt_dt(sd) if st=="COMPLETED" else fmt_dt(sd - timedelta(days=7))))
    return write_csv("production_schedule", rows,
        ["schedule_id","product_id","planned_date","planned_qty","actual_qty","status","created_at","updated_at"])

print("═══ Generating Synthetic Data ═══")
gen_territories()
gen_sales_persons()
gen_territory_assignments()
gen_product_categories()
gen_hsn_codes()
gen_products()
gen_warehouses()
gen_dealers()
gen_dealer_inventory()
gen_inventory()
gen_incoming_stock()
gen_production_capacity()
gen_production_schedule()
print("─── Part 1 complete (tables 1-13) ───")

# ═══════════ TABLE 14: visits ═══════════
def gen_visits():
    RAW_NOTES = [
        "Gupta ji se mila. 2 case 1kg aur 1 case 500g ka order liya. Payment next visit pe denge.",
        "Shop band tha. Neighbor ne bataya Tuesday ko aayenge. Will visit again.",
        "Stock check kiya - 500g khatam hone wala hai. 3 case ka order Tuesday tak chahiye.",
        "Rs 5000 collection kiya. Baki 3500 next week.",
        "Sharma ji ne bola competition ka rate kam hai. Explained quality difference. Will think and order tomorrow.",
        "Visited store. Low stock on 1kg. Ordered 2 cases for delivery Thursday. Also collected Rs 2500 pending.",
        "Quick visit. No order today, stock sufficient. Chai pi aur nikal gaya.",
        "Met owner's son. Father is unwell. Will follow up next week for order.",
        "New month ka order: 3 case 500g, 2 case 1kg. Delivery by Friday. Payment on delivery.",
        "Complaint about last batch - some packets were damp. Assured replacement. Will send 6 pcs tomorrow.",
        "Payment collect kiya Rs 8000 cash. All dues clear. Next order Thursday.",
        "Owner ne kaha 2kg pack slow hai. 500g aur 1kg best seller hai unke yahan.",
        "Kal delivery aaya tha, sab theek hai. 1 case 1kg ka aur order diya hai.",
        "Bohot rush tha shop mein. 5 min mein baat ki. Order phone pe denge shaam ko.",
        "Store closed for renovation. Will reopen in 2 weeks. Check back then.",
        "Competitor ka boy bhi aaya tha. Owner ne bola humare rate theek hai, loyal hain.",
        "2 case 500g immediate chahiye. Drop sale arrange kiya nearby vehicle se.",
        "Festive season stock lena chahte hain. 5 case 500g + 3 case 1kg ka order next week.",
        "Payment pending Rs 12000. Owner ne bola month end pe denge. Reminded about credit limit.",
        "New product inquiry - 2kg pack try karna chahte hain. Ordered 1 case trial.",
    ]
    NEXT_ACTIONS = ["Follow up for order","Collect payment","Deliver pending stock",
                    "Resolve complaint","Schedule next visit","Check stock levels",
                    "Process replacement","Confirm delivery date"]
    rows = []
    R['visits'] = {}
    R['visit_list'] = []
    # Visit frequency by category
    freq = {"A":(8,10),"B":(4,6),"C":(2,4)}
    # Generate visits across 12 months for each active dealer
    all_dates = []
    d = DATA_START
    while d <= DATA_END:
        all_dates.append(d)
        d += timedelta(days=1)
    for dealer in R['active_dealers']:
        cat = dealer['cat']
        fmin, fmax = freq[cat]
        # Generate visits month by month
        for m_offset in range(12):
            month_start = DATA_START + timedelta(days=m_offset*30)
            if month_start > DATA_END: break
            n_visits = random.randint(fmin, fmax)
            for _ in range(n_visits):
                vdate = rand_date(month_start, min(month_start + timedelta(days=29), DATA_END))
                vid = genuuid()
                # Day distribution
                dow = vdate.weekday()
                if dow == 6 and random.random() > 0.02: continue  # skip most Sundays
                vtype_r = random.random()
                vtype = "PLANNED" if vtype_r < 0.85 else ("UNPLANNED" if vtype_r < 0.95 else "DROP_SALE")
                purp_r = random.random()
                if purp_r < 0.45: purpose = "ORDER"
                elif purp_r < 0.75: purpose = "COLLECTION"
                elif purp_r < 0.90: purpose = "RELATIONSHIP"
                elif purp_r < 0.98: purpose = "COMPLAINT"
                else: purpose = "NEW_PRODUCT"
                ci_h = random.randint(9,16)
                ci_m = random.randint(0,59)
                ci = datetime.combine(vdate, time(ci_h, ci_m))
                dur = random.randint(10,45)
                co = ci + timedelta(minutes=dur)
                out_r = random.random()
                if out_r < 0.65: outcome = "SUCCESSFUL"
                elif out_r < 0.85: outcome = "PARTIALLY_SUCCESSFUL"
                elif out_r < 0.97: outcome = "UNSUCCESSFUL"
                else: outcome = "RESCHEDULED"
                ot = 1 if (outcome in ("SUCCESSFUL",) and purpose == "ORDER" and random.random() < 0.5) else 0
                coll = random.randint(500,15000) if purpose == "COLLECTION" else 0
                rows.append(dict(
                    visit_id=vid, dealer_id=dealer['did'], sales_person_id=dealer['rep_id'],
                    visit_date=fmt_dt(vdate), visit_type=vtype, purpose=purpose,
                    check_in_time=fmt_dt(ci), check_out_time=fmt_dt(co), duration_minutes=dur,
                    check_in_latitude=round(dealer['lat']+random.uniform(-0.0005,0.0005),6),
                    check_in_longitude=round(dealer['lng']+random.uniform(-0.0005,0.0005),6),
                    outcome=outcome, order_taken=ot, order_id="",
                    collection_amount=coll, next_action=random.choice(NEXT_ACTIONS),
                    next_visit_date=fmt_dt(vdate+timedelta(days=random.randint(3,10))),
                    follow_up_required=1 if random.random()<0.25 else 0,
                    raw_notes=random.choice(RAW_NOTES),
                    source="TELEGRAM" if random.random()<0.95 else "MANUAL",
                    created_at=fmt_dt(ci), updated_at=fmt_dt(co)))
                R['visits'][vid] = dict(dealer_id=dealer['did'], rep_id=dealer['rep_id'],
                    vdate=vdate, purpose=purpose, outcome=outcome, order_taken=ot)
                R['visit_list'].append(vid)
    # Trim or pad to ~1500
    if len(rows) > 1500:
        rows = rows[:1500]
        R['visit_list'] = R['visit_list'][:1500]
        trimmed_vids = set(r['visit_id'] for r in rows)
        R['visits'] = {k:v for k,v in R['visits'].items() if k in trimmed_vids}
    return write_csv("visits", rows,
        ["visit_id","dealer_id","sales_person_id","visit_date","visit_type","purpose",
         "check_in_time","check_out_time","duration_minutes","check_in_latitude","check_in_longitude",
         "outcome","order_taken","order_id","collection_amount","next_action","next_visit_date",
         "follow_up_required","raw_notes","source","created_at","updated_at"])

# ═══════════ TABLE 15: commitments ═══════════
def gen_commitments():
    rows = []
    R['commitments'] = {}
    R['commitment_list'] = []
    PROD_DESC = {
        "CLN-500G": ["2 cases of 500g","24 pcs 500g","48 pcs 500g","1 case 500g"],
        "CLN-1KG":  ["2 cases of 1kg","12 pcs 1kg","1 case 1kg","3 cases 1kg"],
        "CLN-2KG":  ["1 case 2kg","6 pcs 2kg","12 pcs 2kg"],
    }
    CASE_MULT = {"CLN-500G":24,"CLN-1KG":12,"CLN-2KG":6}
    # Filter visits suitable for commitments
    eligible = [vid for vid,v in R['visits'].items()
                if v['purpose']=="ORDER" and v['outcome'] in ("SUCCESSFUL","PARTIALLY_SUCCESSFUL")]
    random.shuffle(eligible)
    eligible = eligible[:500]
    status_pool = ["CONVERTED"]*275 + ["PARTIAL"]*60 + ["PENDING"]*90 + ["EXPIRED"]*60 + ["CANCELLED"]*15
    random.shuffle(status_pool)
    for i, vid in enumerate(eligible):
        v = R['visits'][vid]
        cid = genuuid()
        pcode_r = random.random()
        pcode = "CLN-500G" if pcode_r<0.50 else ("CLN-1KG" if pcode_r<0.85 else "CLN-2KG")
        pid = R['products'][pcode]
        cm = CASE_MULT[pcode]
        qty = random.choice([cm, cm*2, cm*3])
        st = status_pool[i] if i < len(status_pool) else "CONVERTED"
        eod = v['vdate'] + timedelta(days=random.randint(1,7))
        edd = eod + timedelta(days=random.randint(1,3))
        conf = round(random.uniform(0.70,0.95),2)
        cqty = qty if st=="CONVERTED" else (int(qty*random.uniform(0.5,0.8)) if st=="PARTIAL" else 0)
        conv_date = eod + timedelta(days=random.randint(-3,3)) if st in ("CONVERTED","PARTIAL") else None
        rows.append(dict(
            commitment_id=cid, visit_id=vid, dealer_id=v['dealer_id'],
            sales_person_id=v['rep_id'], product_id=pid, product_category_id=R['category_id'],
            product_description=random.choice(PROD_DESC[pcode]),
            quantity_promised=qty, unit_of_measure="PCS",
            commitment_date=fmt_dt(v['vdate']), expected_order_date=fmt_dt(eod),
            expected_delivery_date=fmt_dt(edd), status=st,
            converted_order_id="",  # filled after orders
            converted_quantity=cqty,
            conversion_date=fmt_dt(conv_date) if conv_date else "",
            confidence_score=conf,
            extraction_source=random.choice(["Order liya","Stock check kiya","Case order diya","Delivery chahiye"]),
            is_consumed=1 if st=="CONVERTED" else 0, consumed_by_order_id="",
            notes="" if random.random()<0.8 else "Follow up required",
            created_at=fmt_dt(v['vdate']),
            updated_at=fmt_dt(conv_date) if conv_date else fmt_dt(v['vdate'])))
        R['commitments'][cid] = dict(status=st, dealer_id=v['dealer_id'], rep_id=v['rep_id'],
                                     product_code=pcode, qty=qty)
        R['commitment_list'].append(cid)
    return write_csv("commitments", rows,
        ["commitment_id","visit_id","dealer_id","sales_person_id","product_id","product_category_id",
         "product_description","quantity_promised","unit_of_measure","commitment_date","expected_order_date",
         "expected_delivery_date","status","converted_order_id","converted_quantity","conversion_date",
         "confidence_score","extraction_source","is_consumed","consumed_by_order_id","notes",
         "created_at","updated_at"])

# ═══════════ TABLE 16 & 17: orders + order_items ═══════════
def gen_orders_and_items():
    DEALER_PRICES = {"CLN-500G":36.00,"CLN-1KG":68.00,"CLN-2KG":128.00}
    CASE_SIZES = {"CLN-500G":24,"CLN-1KG":12,"CLN-2KG":6}
    orders = []
    items = []
    R['orders'] = {}
    R['order_items'] = {}
    R['order_1kg_items'] = []  # for forecast consumption
    # Generate ~900 orders spread over 12 months with seasonal pattern
    order_num = 0
    d = DATA_START
    while d <= DATA_END:
        mm = MONTHLY_MULT.get(d.month, 1.0)
        dm = DOW_MULT.get(d.weekday(), 1.0)
        base = 3
        count = max(0, int(round(base * mm * dm * random.uniform(0.8, 1.2))))
        for _ in range(count):
            order_num += 1
            oid = genuuid()
            dealer = random.choice(R['active_dealers'])
            # Determine status by age
            age = (CURRENT - d).days
            if age > 14:
                sr = random.random()
                st = "DELIVERED" if sr<0.85 else ("CANCELLED" if sr<0.95 else "SHIPPED")
            elif age > 7:
                sr = random.random()
                st = "DELIVERED" if sr<0.50 else ("SHIPPED" if sr<0.85 else ("PROCESSING" if sr<0.95 else "CONFIRMED"))
            else:
                sr = random.random()
                st = "PROCESSING" if sr<0.30 else ("CONFIRMED" if sr<0.65 else ("SHIPPED" if sr<0.90 else "DRAFT"))
            rdd = d + timedelta(days=random.randint(1,3))
            pdd = d + timedelta(days=random.randint(1,4))
            add = pdd + timedelta(days=random.randint(-1,1)) if st=="DELIVERED" else None
            disc_pct = random.uniform(0,5) if random.random()<0.3 else 0
            source = random.choice(["FIELD"]*50+["TELEGRAM"]*45+["PHONE"]*5)
            # Link to commitment (~55%)
            commit_id = ""
            converted_commits = [c for c in R['commitment_list']
                                 if R['commitments'][c]['status'] in ("CONVERTED","PARTIAL")
                                 and R['commitments'][c].get('linked') is None
                                 and R['commitments'][c]['dealer_id']==dealer['did']]
            if converted_commits and random.random() < 0.55:
                commit_id = converted_commits[0]
                R['commitments'][commit_id]['linked'] = oid
            req_app = 1 if disc_pct > 3 else 0
            yr = "2024" if d.year == 2024 else "2025"
            onum = f"ORD-{yr}-{order_num:04d}"
            # Generate items
            n_items_r = random.random()
            n_items = 1 if n_items_r<0.60 else (2 if n_items_r<0.95 else 3)
            prods_in_order = []
            if n_items >= 1: prods_in_order.append("CLN-500G" if random.random()<0.56 else "CLN-1KG")
            if n_items >= 2:
                second = "CLN-1KG" if prods_in_order[0]=="CLN-500G" else "CLN-500G"
                if random.random()<0.25: second = "CLN-2KG"
                prods_in_order.append(second)
            if n_items >= 3:
                prods_in_order.append("CLN-2KG")
            subtotal = 0
            order_item_rows = []
            for pcode in prods_in_order:
                oiid = genuuid()
                cs = CASE_SIZES[pcode]
                qty = random.choice([cs, cs*2, cs*3, cs*4])
                up = DEALER_PRICES[pcode]
                item_disc = disc_pct
                disc_amt = round(up * qty * item_disc / 100, 2)
                tax_amt = round((up * qty - disc_amt) * 0.18, 2)
                lt = round(up * qty - disc_amt + tax_amt, 2)
                subtotal += round(up * qty, 2)
                qc = qty if st not in ("DRAFT",) else int(qty * random.uniform(0.95,1.0))
                qs = qc if st in ("SHIPPED","DELIVERED") else 0
                qd = qs if st == "DELIVERED" else 0
                row = dict(order_item_id=oiid, order_id=oid, product_id=R['products'][pcode],
                           quantity_ordered=qty, quantity_confirmed=qc, quantity_shipped=qs,
                           quantity_delivered=qd, unit_price=up, discount_percent=round(item_disc,2),
                           discount_amount=disc_amt, tax_rate=18, tax_amount=tax_amt,
                           line_total=lt, original_quantity="", split_reason="", notes="",
                           created_at=fmt_dt(d))
                order_item_rows.append(row)
                items.append(row)
                R['order_items'][oiid] = dict(oid=oid, pcode=pcode, qty=qty, date=d, line_total=lt, qty_delivered=qd)
                if pcode == "CLN-1KG":
                    R['order_1kg_items'].append(dict(oiid=oiid, oid=oid, qty=qty, date=d))
            disc_total = round(subtotal * disc_pct / 100, 2)
            tax_total = round((subtotal - disc_total) * 0.18, 2)
            total = round(subtotal - disc_total + tax_total, 2)
            pay_st = "PAID" if st == "DELIVERED" and random.random()<0.7 else ("PARTIAL" if st in ("DELIVERED","SHIPPED") else "UNPAID")
            orders.append(dict(
                order_id=oid, order_number=onum, dealer_id=dealer['did'],
                sales_person_id=dealer['rep_id'], order_date=fmt_dt(d),
                requested_delivery_date=fmt_dt(rdd), promised_delivery_date=fmt_dt(pdd),
                actual_delivery_date=fmt_dt(add) if add else "",
                subtotal=round(subtotal,2), discount_amount=disc_total, discount_percent=round(disc_pct,2),
                tax_amount=tax_total, total_amount=total, status=st, payment_status=pay_st,
                source=source, commitment_id=commit_id, parent_order_id="", is_split=0,
                split_sequence="", requires_approval=req_app,
                approved_by=R['manager_id'] if req_app else "",
                approved_at=fmt_dt(datetime.combine(d,time(random.randint(10,17),random.randint(0,59)))) if req_app else "",
                notes="" if random.random()<0.7 else "Rush order" if random.random()<0.5 else "Regular monthly order",
                created_at=fmt_dt(d), updated_at=fmt_dt(add) if add else fmt_dt(d)))
            R['orders'][oid] = dict(dealer_id=dealer['did'], date=d, status=st, total=total,
                                    pay_st=pay_st, onum=onum, rep_id=dealer['rep_id'])
        d += timedelta(days=1)
    # Trim to ~900
    if len(orders) > 900:
        orders = orders[:900]
        valid_oids = {o['order_id'] for o in orders}
        items = [it for it in items if it['order_id'] in valid_oids]
        R['orders'] = {k:v for k,v in R['orders'].items() if k in valid_oids}
        R['order_items'] = {k:v for k,v in R['order_items'].items() if v['oid'] in valid_oids}
        R['order_1kg_items'] = [x for x in R['order_1kg_items'] if x['oid'] in valid_oids]
    R['order_list'] = [o['order_id'] for o in orders]
    write_csv("orders", orders,
        ["order_id","order_number","dealer_id","sales_person_id","order_date",
         "requested_delivery_date","promised_delivery_date","actual_delivery_date",
         "subtotal","discount_amount","discount_percent","tax_amount","total_amount",
         "status","payment_status","source","commitment_id","parent_order_id","is_split",
         "split_sequence","requires_approval","approved_by","approved_at","notes","created_at","updated_at"])
    write_csv("order_items", items,
        ["order_item_id","order_id","product_id","quantity_ordered","quantity_confirmed",
         "quantity_shipped","quantity_delivered","unit_price","discount_percent","discount_amount",
         "tax_rate","tax_amount","line_total","original_quantity","split_reason","notes","created_at"])

# ═══════════ TABLE 18: order_splits ═══════════
def gen_order_splits():
    rows = []
    # Pick ~15 orders to be splits
    eligible = [oid for oid,o in R['orders'].items() if o['status'] in ("DELIVERED","SHIPPED")]
    split_oids = random.sample(eligible, min(15, len(eligible)))
    R['split_orders'] = set()
    for oid in split_oids:
        o = R['orders'][oid]
        split_oid = genuuid()
        R['split_orders'].add(oid)
        reason = "CAPACITY_CONSTRAINT" if random.random()<0.6 else "STOCK_UNAVAILABLE"
        orig_qty = random.randint(24,72)
        split_qty = int(orig_qty * random.uniform(0.3,0.5))
        disc = round(random.uniform(2,3),1) if random.random()<0.5 else 0
        disc_app = 1 if disc>0 and random.random()<0.8 else 0
        rows.append(dict(
            split_id=genuuid(), original_order_id=oid, split_order_id=split_oid,
            split_reason=reason, original_quantity=orig_qty,
            original_delivery_date=fmt_dt(o['date']+timedelta(days=2)),
            split_quantity=split_qty,
            new_delivery_date=fmt_dt(o['date']+timedelta(days=random.randint(4,6))),
            discount_offered=disc, discount_approved=disc_app,
            discount_approved_by=R['manager_id'] if disc_app else "",
            discount_approved_at=fmt_dt(datetime.combine(o['date'],time(random.randint(10,16),0))) if disc_app else "",
            alert_id="", created_by=o['rep_id'],
            created_at=fmt_dt(o['date'])))
    return write_csv("order_splits", rows,
        ["split_id","original_order_id","split_order_id","split_reason","original_quantity",
         "original_delivery_date","split_quantity","new_delivery_date","discount_offered",
         "discount_approved","discount_approved_by","discount_approved_at","alert_id",
         "created_by","created_at"])

# ═══════════ TABLE 19: invoices ═══════════
def gen_invoices():
    rows = []
    R['invoices'] = {}
    inv_num = 0
    overdue_count = 0
    invoice_statuses = ["CONFIRMED","PROCESSING","SHIPPED","DELIVERED"]
    for oid, o in sorted(R['orders'].items(), key=lambda x: x[1]['date']):
        if o['status'] not in invoice_statuses: continue
        inv_num += 1
        iid = genuuid()
        idate = o['date']
        credit_days = random.choice([7,15])
        due = idate + timedelta(days=credit_days)
        sub = o['total'] / 1.18 * 1.0  # approximate
        disc = sub * 0.02 if random.random()<0.2 else 0
        taxable = sub - disc
        cgst = round(taxable * 0.09, 2)
        sgst = round(taxable * 0.09, 2)
        total_tax = round(cgst + sgst, 2)
        total = round(taxable + total_tax, 2)
        # Status - force some overdue for demo
        is_overdue = CURRENT > due and o['pay_st'] != "PAID"
        if o['pay_st'] == "PAID": ist = "PAID"
        elif o['pay_st'] == "PARTIAL": ist = "PARTIAL"
        elif is_overdue: ist = "OVERDUE"
        else: ist = "PENDING"
        # Force ~15 OVERDUE invoices from older non-PAID orders
        age = (CURRENT - idate).days
        if ist not in ("PAID","OVERDUE") and age > 20 and overdue_count < 15:
            ist = "OVERDUE"
            overdue_count += 1
        yr = "2024" if idate.year==2024 else "2025"
        paid_amt = total if ist=="PAID" else (round(total*random.uniform(0.3,0.7),2) if ist=="PARTIAL" else 0)
        rows.append(dict(
            invoice_id=iid, invoice_number=f"INV-{yr}-{inv_num:04d}",
            order_id=oid, dealer_id=o['dealer_id'],
            invoice_date=fmt_dt(idate), due_date=fmt_dt(due),
            subtotal=round(sub,2), discount_amount=round(disc,2),
            cgst_amount=cgst, sgst_amount=sgst, igst_amount=0, cess_amount=0,
            total_tax=total_tax, total_amount=total, amount_paid=paid_amt,
            status=ist, created_at=fmt_dt(idate), updated_at=fmt_dt(idate)))
        R['invoices'][iid] = dict(oid=oid, dealer_id=o['dealer_id'], total=total,
                                   paid=paid_amt, status=ist, date=idate, due=due)
        if inv_num >= 850: break
    return write_csv("invoices", rows,
        ["invoice_id","invoice_number","order_id","dealer_id","invoice_date","due_date",
         "subtotal","discount_amount","cgst_amount","sgst_amount","igst_amount","cess_amount",
         "total_tax","total_amount","amount_paid","status","created_at","updated_at"])

# ═══════════ TABLE 20: payments ═══════════
def gen_payments():
    rows = []
    R['payments'] = {}
    BANKS = ["State Bank of India","HDFC Bank","ICICI Bank","Punjab National Bank",
             "Bank of Baroda","Axis Bank","Kotak Mahindra Bank","Yes Bank"]
    pay_num = 0
    invoice_list = list(R['invoices'].items())
    random.shuffle(invoice_list)
    # Generate ~1000 payments
    for iid, inv in invoice_list:
        if pay_num >= 1000: break
        n_pays = 1 if inv['status'] in ("PAID","PENDING") else random.randint(1,2)
        remaining = inv['total']
        for _ in range(n_pays):
            if pay_num >= 1000: break
            pay_num += 1
            pid = genuuid()
            amt = round(min(remaining, random.uniform(500,25000)),2)
            remaining -= amt
            pdate = rand_date(inv['date'], min(inv['due']+timedelta(days=7), CURRENT))
            mode_r = random.random()
            mode = "CASH" if mode_r<0.35 else ("UPI" if mode_r<0.75 else ("NEFT" if mode_r<0.90 else "CHEQUE"))
            ref = "" if mode=="CASH" else f"TXN{random.randint(100000,999999)}"
            bank = random.choice(BANKS) if mode in ("CHEQUE","NEFT") else ""
            coll = random.choice(list(R['sales_persons'].values())) if mode=="CASH" else ""
            st_r = random.random()
            st = "COMPLETED" if st_r<0.97 else ("PENDING" if st_r<0.99 else "BOUNCED")
            yr = "2024" if pdate.year==2024 else "2025"
            rows.append(dict(
                payment_id=pid, payment_number=f"PAY-{yr}-{pay_num:04d}",
                dealer_id=inv['dealer_id'], invoice_id=iid, amount=amt,
                payment_date=fmt_dt(pdate), payment_mode=mode,
                reference_number=ref, bank_name=bank, collected_by=coll,
                visit_id="", status=st, notes="",
                created_at=fmt_dt(pdate), updated_at=fmt_dt(pdate)))
    # Add advance payments (5%)
    for _ in range(min(50, 1000 - pay_num)):
        pay_num += 1
        dealer = random.choice(R['active_dealers'])
        pdate = rand_date(DATA_START, DATA_END)
        amt = round(random.uniform(500,10000),2)
        yr = "2024" if pdate.year==2024 else "2025"
        rows.append(dict(
            payment_id=genuuid(), payment_number=f"PAY-{yr}-{pay_num:04d}",
            dealer_id=dealer['did'], invoice_id="", amount=amt,
            payment_date=fmt_dt(pdate), payment_mode=random.choice(["CASH","UPI"]),
            reference_number="", bank_name="", collected_by="",
            visit_id="", status="COMPLETED", notes="Advance payment",
            created_at=fmt_dt(pdate), updated_at=fmt_dt(pdate)))
    return write_csv("payments", rows,
        ["payment_id","payment_number","dealer_id","invoice_id","amount","payment_date",
         "payment_mode","reference_number","bank_name","collected_by","visit_id","status",
         "notes","created_at","updated_at"])

# ═══════════ TABLE 21: issues ═══════════
def gen_issues():
    SUBJ = {
        "DELIVERY": ["Late delivery - Order {}","Partial delivery received","Wrong delivery address","Missing items in delivery"],
        "QUALITY": ["Damaged packaging","Damp packets in batch","Different color powder","Seal broken on packets"],
        "PRICING": ["Invoice amount mismatch","Discount not applied","Wrong MRP printed","Rate card outdated"],
        "SERVICE": ["Rude behavior by delivery person","No response on complaint","Delayed replacement","Sales rep not visiting"],
    }
    rows = []
    for i in range(40):
        itype_r = random.random()
        itype = "DELIVERY" if itype_r<0.35 else ("QUALITY" if itype_r<0.65 else ("PRICING" if itype_r<0.85 else "SERVICE"))
        pri_r = random.random()
        pri = "CRITICAL" if pri_r<0.05 else ("HIGH" if pri_r<0.25 else ("MEDIUM" if pri_r<0.80 else "LOW"))
        dealer = random.choice(R['active_dealers'])
        st_r = random.random()
        st = "RESOLVED" if st_r<0.70 else ("CLOSED" if st_r<0.85 else ("OPEN" if st_r<0.95 else "IN_PROGRESS"))
        cr = rand_date(DATA_START, DATA_END)
        res_at = rand_date(cr, min(cr+timedelta(days=14),CURRENT)) if st in ("RESOLVED","CLOSED") else None
        subj_tmpl = random.choice(SUBJ[itype])
        # Pick an order for delivery/quality
        sample_onum = f"ORD-2024-{random.randint(1,900):04d}"
        subj = subj_tmpl.format(sample_onum) if "{}" in subj_tmpl else subj_tmpl
        oid_ref = random.choice(R['order_list']) if itype in ("DELIVERY","QUALITY") else ""
        pid_ref = R['products'][random.choice(["CLN-500G","CLN-1KG","CLN-2KG"])] if itype=="QUALITY" else ""
        vid_ref = random.choice(R['visit_list']) if random.random()<0.7 else ""
        rows.append(dict(
            issue_id=genuuid(), dealer_id=dealer['did'], sales_person_id=dealer['rep_id'],
            visit_id=vid_ref, issue_type=itype, priority=pri, subject=subj,
            description=f"Issue reported by {dealer['code']}: {subj}",
            order_id=oid_ref, product_id=pid_ref, status=st,
            assigned_to=R['manager_id'],
            resolution=f"Issue resolved. Replacement/credit provided." if st in ("RESOLVED","CLOSED") else "",
            resolved_at=fmt_dt(res_at) if res_at else "",
            created_at=fmt_dt(cr), updated_at=fmt_dt(res_at) if res_at else fmt_dt(cr)))
    return write_csv("issues", rows,
        ["issue_id","dealer_id","sales_person_id","visit_id","issue_type","priority","subject",
         "description","order_id","product_id","status","assigned_to","resolution","resolved_at",
         "created_at","updated_at"])

gen_visits()
gen_commitments()
gen_orders_and_items()
gen_order_splits()
gen_invoices()
gen_payments()
gen_issues()
print("─── Part 2 complete (tables 14-21) ───")

# ═══════════ TABLE 22: vehicles ═══════════
def gen_vehicles():
    R['vehicles'] = {}
    specs = [
        ("DL-01-AB-1234","MINI_TRUCK",500,1000,6,"Ramu Prasad","9899123456","2023-01-01"),
        ("DL-01-CD-5678","VAN",250,500,3,"Shyam Lal","9899654321","2023-06-01"),
    ]
    rows = []
    for vnum,vtype,cap_u,cap_w,cap_v,driver,phone,created in specs:
        vid = genuuid()
        R['vehicles'][vnum] = vid
        rows.append(dict(vehicle_id=vid, vehicle_number=vnum, vehicle_type=vtype,
                         capacity_units=cap_u, capacity_weight_kg=cap_w, capacity_volume_cbm=cap_v,
                         warehouse_id=R['warehouse_id'], driver_name=driver, driver_phone=phone,
                         status="AVAILABLE", is_active=1, created_at=f"{created} 00:00:00"))
    R['vehicle_ids'] = list(R['vehicles'].values())
    R['vehicle_caps'] = {R['vehicles']["DL-01-AB-1234"]:500, R['vehicles']["DL-01-CD-5678"]:250}
    return write_csv("vehicles", rows,
        ["vehicle_id","vehicle_number","vehicle_type","capacity_units","capacity_weight_kg",
         "capacity_volume_cbm","warehouse_id","driver_name","driver_phone","status","is_active","created_at"])

# ═══════════ TABLE 23: delivery_routes ═══════════
def gen_delivery_routes():
    rows = []
    R['routes'] = {}
    # ~4 routes/week × 50 weeks = 200
    d = DATA_START
    route_count = 0
    while d <= DATA_END and route_count < 200:
        if d.weekday() < 6:  # Mon-Sat
            if random.random() < 0.65:  # ~4/week avg
                route_count += 1
                rid = genuuid()
                vid = random.choice(R['vehicle_ids'])
                cap = R['vehicle_caps'][vid]
                util = int(cap * random.uniform(0.5, 0.9))
                is_past = d < CURRENT
                st = "COMPLETED" if is_past and random.random()<0.95 else ("CANCELLED" if is_past else "PLANNED")
                pst = time(random.choice([7,8]),0)
                ast = time(max(0, min(23, pst.hour + random.randint(-1,1))), random.randint(0,59)) if st=="COMPLETED" else None
                pet = time(random.randint(14,18),0)
                dur_h = random.randint(6,10)
                aet = time(min(23,(ast.hour if ast else 8)+dur_h), random.randint(0,59)) if st=="COMPLETED" else None
                n_stops = random.randint(4,10)
                total_km = round(random.uniform(20,60),1)
                rows.append(dict(
                    route_id=rid, route_date=fmt_dt(d), vehicle_id=vid,
                    total_capacity=cap, utilized_capacity=util, status=st,
                    planned_start_time=pst.strftime("%H:%M:%S"),
                    actual_start_time=ast.strftime("%H:%M:%S") if ast else "",
                    planned_end_time=pet.strftime("%H:%M:%S"),
                    actual_end_time=aet.strftime("%H:%M:%S") if aet else "",
                    total_distance_km=total_km, total_stops=n_stops,
                    created_at=fmt_dt(d - timedelta(days=1)),
                    updated_at=fmt_dt(d) if st=="COMPLETED" else fmt_dt(d - timedelta(days=1))))
                R['routes'][rid] = dict(date=d, status=st, n_stops=n_stops)
        d += timedelta(days=1)
    return write_csv("delivery_routes", rows,
        ["route_id","route_date","vehicle_id","total_capacity","utilized_capacity","status",
         "planned_start_time","actual_start_time","planned_end_time","actual_end_time",
         "total_distance_km","total_stops","created_at","updated_at"])

# ═══════════ TABLE 24: route_stops ═══════════
def gen_route_stops():
    rows = []
    for rid, route in R['routes'].items():
        n = route['n_stops']
        # Pick geographically clustered dealers
        territory = random.choice(list(R['territories'].keys()))
        area_dealers = [d for d in R['active_dealers'] if d['territory']==territory]
        if len(area_dealers) < n:
            area_dealers = R['active_dealers'][:n]
        stops = random.sample(area_dealers, min(n, len(area_dealers)))
        start_h = 8
        for seq, dealer in enumerate(stops, 1):
            sid = genuuid()
            st_type = "DROP_SALE" if random.random()<0.05 else "DELIVERY"
            qty = random.randint(6,48)
            qd = qty if route['status']=="COMPLETED" else 0
            pa = time(min(23, start_h + seq - 1), random.randint(0,45))
            aa_min = max(0, min(59, pa.minute+random.randint(-15,15)))
            aa = time(pa.hour, aa_min) if route['status']=="COMPLETED" else None
            dep_min = min(59, (aa.minute if aa else pa.minute)+random.randint(10,20))
            dep = time(min(23, aa.hour if aa else pa.hour), dep_min) if route['status']=="COMPLETED" else None
            # Pick a random order for this dealer
            oid = ""
            for o_id, o in R['orders'].items():
                if o['dealer_id'] == dealer['did'] and o['status'] in ("SHIPPED","DELIVERED"):
                    oid = o_id; break
            rows.append(dict(
                stop_id=sid, route_id=rid, dealer_id=dealer['did'],
                order_id=oid, stop_sequence=seq, stop_type=st_type,
                quantity_to_deliver=qty, quantity_delivered=qd,
                status="COMPLETED" if route['status']=="COMPLETED" else "PLANNED",
                planned_arrival=pa.strftime("%H:%M:%S"),
                actual_arrival=aa.strftime("%H:%M:%S") if aa else "",
                departure_time=dep.strftime("%H:%M:%S") if dep else "",
                is_drop_sale=1 if st_type=="DROP_SALE" else 0,
                drop_sale_source=oid if st_type=="DROP_SALE" else "",
                notes="", created_at=fmt_dt(route['date']),
                updated_at=fmt_dt(route['date'])))
    return write_csv("route_stops", rows,
        ["stop_id","route_id","dealer_id","order_id","stop_sequence","stop_type",
         "quantity_to_deliver","quantity_delivered","status","planned_arrival","actual_arrival",
         "departure_time","is_drop_sale","drop_sale_source","notes","created_at","updated_at"])

# ═══════════ TABLE 25: alerts ═══════════
def gen_alerts():
    rows = []
    ALERT_TYPES = ["SPLIT_ORDER_APPROVAL"]*28 + ["DISCOUNT_APPROVAL"]*20 + \
                  ["LOW_STOCK"]*16 + ["OVERDUE_PAYMENT"]*12 + ["CREDIT_LIMIT_BREACH"]*4
    random.shuffle(ALERT_TYPES)
    rep_ids = [R['sales_persons'][c] for c in ["EMP002","EMP003","EMP004","EMP005"]]
    for i in range(80):
        atype = ALERT_TYPES[i]
        pri_r = random.random()
        pri = "URGENT" if pri_r<0.10 else ("HIGH" if pri_r<0.40 else ("MEDIUM" if pri_r<0.85 else "LOW"))
        cr = rand_date(DATA_START, DATA_END)
        st_r = random.random()
        st = "APPROVED" if st_r<0.65 else ("REJECTED" if st_r<0.75 else ("PENDING" if st_r<0.95 else "EXPIRED"))
        resp_at = rand_date(cr, min(cr+timedelta(days=2), CURRENT)) if st in ("APPROVED","REJECTED") else None
        # Entity
        if atype in ("SPLIT_ORDER_APPROVAL","DISCOUNT_APPROVAL"):
            etype, eid = "ORDER", random.choice(R['order_list'])
        elif atype in ("OVERDUE_PAYMENT","CREDIT_LIMIT_BREACH"):
            etype, eid = "DEALER", random.choice(R['active_dealers'])['did']
        else:
            etype, eid = "PRODUCT", R['products'][random.choice(["CLN-500G","CLN-1KG","CLN-2KG"])]
        titles = {
            "SPLIT_ORDER_APPROVAL": f"Split Order Request - ORD-2024-{random.randint(1,900):04d}",
            "DISCOUNT_APPROVAL": f"Discount Approval - {random.randint(3,5)}% for dealer",
            "LOW_STOCK": f"Low Stock Alert - CleanMax {random.choice(['500g','1kg','2kg'])}",
            "OVERDUE_PAYMENT": f"Overdue Payment - Rs {random.randint(5000,25000)}",
            "CREDIT_LIMIT_BREACH": f"Credit Limit Exceeded - dealer",
        }
        rows.append(dict(
            alert_id=genuuid(), alert_type=atype, priority=pri,
            assigned_to=R['manager_id'], created_by=random.choice(rep_ids),
            entity_type=etype, entity_id=eid,
            title=titles[atype], message=f"Action required: {titles[atype]}",
            action_required="Review and approve" if "APPROVAL" in atype else "Review and take action",
            context_data="{}", status=st,
            response=st if st in ("APPROVED","REJECTED") else "",
            response_notes="Approved by manager" if st=="APPROVED" else ("Rejected" if st=="REJECTED" else ""),
            responded_at=fmt_dt(resp_at) if resp_at else "",
            notification_sent=1, notification_channel="TELEGRAM",
            notification_sent_at=fmt_dt(cr),
            expires_at=fmt_dt(cr+timedelta(hours=random.randint(24,48))),
            created_at=fmt_dt(cr),
            updated_at=fmt_dt(resp_at) if resp_at else fmt_dt(cr)))
    return write_csv("alerts", rows,
        ["alert_id","alert_type","priority","assigned_to","created_by","entity_type","entity_id",
         "title","message","action_required","context_data","status","response","response_notes",
         "responded_at","notification_sent","notification_channel","notification_sent_at",
         "expires_at","created_at","updated_at"])

# ═══════════ TABLE 26: sales_targets ═══════════
def gen_sales_targets():
    rows = []
    targets = {
        "EMP002": ("North Delhi", 200000),
        "EMP003": ("South Delhi", 180000),
        "EMP004": ("East Delhi", 180000),
        "EMP005": ("West Delhi", 220000),
    }
    for m_offset in range(12):
        month_start = date(2024, 3, 1) + timedelta(days=m_offset*30)
        if month_start.month > 12: continue
        try:
            ps = date(month_start.year, month_start.month, 1)
        except:
            continue
        # Compute last day of month
        if ps.month == 12:
            pe = date(ps.year, 12, 31)
        else:
            pe = date(ps.year, ps.month + 1, 1) - timedelta(days=1)
        is_past = pe < CURRENT
        for code, (tname, target_val) in targets.items():
            sid = R['sales_persons'][code]
            tid = R['territories'][tname]
            achieved = round(target_val * random.uniform(0.70, 1.20), 2) if is_past else round(target_val * random.uniform(0.2, 0.7), 2)
            ach_pct = round(achieved / target_val * 100, 1)
            rows.append(dict(
                target_id=genuuid(), sales_person_id=sid, territory_id=tid,
                product_id="", product_category_id="", period_type="MONTHLY",
                period_start=fmt_dt(ps), period_end=fmt_dt(pe),
                target_type="REVENUE", target_value=target_val,
                achieved_value=achieved, achievement_percent=ach_pct, notes="",
                created_at=fmt_dt(ps),
                updated_at=fmt_dt(pe) if is_past else fmt_dt(CURRENT)))
    return write_csv("sales_targets", rows,
        ["target_id","sales_person_id","territory_id","product_id","product_category_id",
         "period_type","period_start","period_end","target_type","target_value",
         "achieved_value","achievement_percent","notes","created_at","updated_at"])

# ═══════════ TABLE 27: dealer_health_scores ═══════════
def gen_dealer_health_scores():
    rows = []
    score_ranges = {"A":(75,95),"B":(60,85),"C":(35,75)}
    months = []
    for m in range(10):
        dt = date(2024,5,1) + timedelta(days=m*30)
        try:
            months.append(date(dt.year, dt.month, 1))
        except:
            pass
    for dealer in R['active_dealers']:
        cat = dealer['cat']
        smin, smax = score_ranges[cat]
        for calc_date in months:
            ps = random.randint(smin, smax)
            ofs = random.randint(smin, smax)
            ovs = random.randint(smin, smax)
            cs = random.randint(smin, smax)
            es = random.randint(smin, smax)
            overall = round(ps*0.25 + ofs*0.20 + ovs*0.20 + cs*0.20 + es*0.15, 1)
            if overall >= 80: hs = "EXCELLENT"
            elif overall >= 65: hs = "GOOD"
            elif overall >= 50: hs = "AVERAGE"
            elif overall >= 35: hs = "AT_RISK"
            else: hs = "CRITICAL"
            req_att = 1 if hs in ("AT_RISK","CRITICAL") else 0
            att_reason = ""
            if req_att:
                att_reason = random.choice(["Overdue payments","No orders in 30 days",
                                            "Low order frequency","Declining order value",
                                            "Poor commitment fulfillment"])
            rows.append(dict(
                score_id=genuuid(), dealer_id=dealer['did'],
                calculated_date=fmt_dt(calc_date),
                payment_score=ps, order_frequency_score=ofs, order_value_score=ovs,
                commitment_score=cs, engagement_score=es,
                overall_score=overall, health_status=hs,
                total_outstanding=round(random.uniform(0,50000),2),
                days_since_last_order=random.randint(1,30),
                days_since_last_visit=random.randint(1,14),
                avg_order_value_30d=round(random.uniform(2000,15000),2),
                commitment_fulfillment_rate_90d=round(random.uniform(0.55,0.95),2),
                requires_attention=req_att, attention_reason=att_reason,
                created_at=fmt_dt(calc_date)))
    return write_csv("dealer_health_scores", rows,
        ["score_id","dealer_id","calculated_date","payment_score","order_frequency_score",
         "order_value_score","commitment_score","engagement_score","overall_score","health_status",
         "total_outstanding","days_since_last_order","days_since_last_visit",
         "avg_order_value_30d","commitment_fulfillment_rate_90d","requires_attention",
         "attention_reason","created_at"])

# ═══════════ TABLE 28: weekly_sales_actuals ═══════════
def gen_weekly_sales_actuals():
    """Aggregate order_items into weekly sales per product for ML training."""
    rows = []
    week_start = date(2024, 3, 4)  # First Monday
    FESTIVAL_MONTHS = {3, 10}  # Holi (Mar), Diwali (Oct)
    product_codes = ["CLN-500G", "CLN-1KG", "CLN-2KG"]
    for w in range(52):
        ws = week_start + timedelta(weeks=w)
        we = ws + timedelta(days=6)
        if ws > DATA_END: break
        is_festival = 1 if ws.month in FESTIVAL_MONTHS else 0
        for pcode in product_codes:
            pid = R['products'][pcode]
            # Aggregate from order_items registry
            qty_ordered = 0
            qty_delivered = 0
            revenue = 0.0
            order_ids = set()
            for oiid, oi in R['order_items'].items():
                if oi['pcode'] == pcode and ws <= oi['date'] <= we:
                    qty_ordered += oi['qty']
                    qty_delivered += oi['qty_delivered']
                    revenue += oi['line_total']
                    order_ids.add(oi['oid'])
            rows.append(dict(
                week_id=genuuid(), week_start=fmt_dt(ws), week_end=fmt_dt(we),
                week_number=w+1, year=ws.year, month=ws.month,
                product_id=pid, product_code=pcode,
                quantity_ordered=qty_ordered, quantity_delivered=qty_delivered,
                order_count=len(order_ids), revenue=round(revenue, 2),
                is_festival_week=is_festival))
    return write_csv("weekly_sales_actuals", rows,
        ["week_id","week_start","week_end","week_number","year","month",
         "product_id","product_code","quantity_ordered","quantity_delivered",
         "order_count","revenue","is_festival_week"])

# ═══════════ TABLE 30: consumption_config ═══════════
def gen_consumption_config():
    rows = [dict(
        config_id=genuuid(), product_id="", dealer_id="",
        backward_days=7, forward_days=3, direction_priority="BACKWARD_FIRST",
        quantity_tolerance_pct=25, expire_after_days=10,
        effective_from="2024-01-01", effective_to="",
        created_at="2024-01-01 00:00:00")]
    return write_csv("consumption_config", rows,
        ["config_id","product_id","dealer_id","backward_days","forward_days",
         "direction_priority","quantity_tolerance_pct","expire_after_days",
         "effective_from","effective_to","created_at"])

# ═══════════ TABLE 31: system_settings ═══════════
def gen_system_settings():
    rows = [
        dict(setting_key="DEFAULT_CREDIT_DAYS", setting_value="15", setting_type="INTEGER",
             description="Default payment terms in days"),
        dict(setting_key="DEFAULT_CREDIT_LIMIT", setting_value="25000", setting_type="FLOAT",
             description="Default credit limit for new dealers"),
        dict(setting_key="COMMITMENT_EXPIRY_DAYS", setting_value="10", setting_type="INTEGER",
             description="Days after expected date to expire commitment"),
        dict(setting_key="DROP_SALE_RADIUS_KM", setting_value="3", setting_type="FLOAT",
             description="Radius in KM to search for drop sale opportunities"),
        dict(setting_key="DROP_SALE_MIN_SPARE_CAPACITY", setting_value="30", setting_type="FLOAT",
             description="Minimum spare capacity to trigger drop sale"),
        dict(setting_key="HEALTH_SCORE_REFRESH_HOURS", setting_value="24", setting_type="INTEGER",
             description="Hours between dealer health score refresh"),
        dict(setting_key="FORECAST_CONSUMPTION_BACKWARD_DAYS", setting_value="7", setting_type="INTEGER",
             description="Default backward consumption days"),
        dict(setting_key="FORECAST_CONSUMPTION_FORWARD_DAYS", setting_value="3", setting_type="INTEGER",
             description="Default forward consumption days"),
    ]
    return write_csv("system_settings", rows,
        ["setting_key","setting_value","setting_type","description"])

# ═══════════ README ═══════════
def gen_readme():
    readme = f"""# Synthetic Data for SupplyChain Copilot

## Generation Details
- Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- Generator: Synthetic Data Script
- Business Context: Small MSME detergent manufacturer in Delhi NCR

## Record Counts
| Table | Records |
|-------|---------|
| territories | 5 |
| sales_persons | 5 |
| territory_assignments | 5 |
| product_categories | 1 |
| hsn_codes | 1 |
| products | 3 |
| warehouses | 1 |
| dealers | 45 |
| dealer_inventory | ~120 |
| inventory | 3 |
| incoming_stock | 10 |
| production_capacity | 3 |
| production_schedule | 150 |
| visits | ~1500 |
| commitments | 500 |
| orders | ~900 |
| order_items | ~1500 |
| order_splits | ~15 |
| invoices | ~850 |
| payments | ~1000 |
| issues | 40 |
| vehicles | 2 |
| delivery_routes | ~200 |
| route_stops | ~1200 |
| alerts | 80 |
| sales_targets | 48 |
| dealer_health_scores | ~400 |
| weekly_sales_actuals | 156 |
| consumption_config | 1 |
| system_settings | 8 |
| **TOTAL** | **~7,700** |

## Data Characteristics
- Time Range: 2024-03-01 to 2025-02-24 (12 months)
- Geography: Delhi NCR only
- Products: 3 SKUs (500g, 1kg, 2kg) of CleanMax Detergent
- Training Data: weekly_sales_actuals (filter to CLN-1KG for 52 rows)
- Seasonal patterns: Diwali (Oct) and Holi (Mar) peaks, Monsoon (Jun-Jul) dips

## Key IDs for Testing
- Manager (Rajesh Kumar): {R['manager_id']}
- 1kg Product (CLN-1KG): {R['PRIMARY_FORECAST_PRODUCT_ID']}
- Primary Warehouse: {R['warehouse_id']}
"""
    with open(OUTPUT_DIR / "README.md", "w", encoding="utf-8") as f:
        f.write(readme)
    print("  README.md generated")

# ─── Run Part 3 ───
gen_vehicles()
gen_delivery_routes()
gen_route_stops()
gen_alerts()
gen_sales_targets()
gen_dealer_health_scores()
gen_weekly_sales_actuals()
gen_consumption_config()
gen_system_settings()
gen_readme()
print("═══ ALL DONE ═══")
