# SupplyChain Copilot

An AI-powered sales and production copilot for Indian MSMEs — built for CleanMax, a B2B detergent distribution brand operating across Delhi NCR.

The system gives **sales reps** a Telegram bot for natural language field reporting (Hinglish supported), and gives **managers** a React dashboard with live metrics and an embedded AI chat assistant backed by AWS Bedrock multi-agent orchestration.

---

## What It Does

### For Sales Reps (Telegram Bot)
- Send visit reports in plain language or Hinglish — the bot understands and captures structured data
- Ask for dealer briefings before a visit ("tell me about Raj Traders")
- Get AI-planned visit routes for the day
- Create commitments and orders conversationally
- Receive alerts when a dealer is at risk

### For Managers (Web Dashboard)
- **Sales tab**: KPI cards (revenue, collections, targets), dealer network health, commitment pipeline, sales team performance, revenue trends
- **Production tab**: Production KPIs, daily planned vs actual output, 6-month demand/supply chart, per-product inventory and days-of-cover
- **AI Copilot chat**: Ask anything — team performance, at-risk dealers, forecast, demand gaps — and get answers from live data via Bedrock agents
- **Demand Forecast**: Per-product weekly forecasts with seasonal adjustments (Holi/Diwali boosts)

---

## Architecture

```
Browser (React)          Telegram
      |                      |
      |                      v
      |          Lambda Function URL (120s timeout)
      |          scm-telegram-webhook
      |                      |
      v                      |
API Gateway (29s limit)      |
scm-dashboard-api Lambda     |
      |                      |
      +----------+-----------+
                 |
                 v
      Bedrock Supervisor Agent
      (CS4Z87AWWT / claude-sonnet-4-6)
         |        |        |        |
         v        v        v        v
   Dealer     Visit     Order   Manager
   Intel.    Capture  Planning Analytics
         \       |      /        /
          \      |     /        /
           v     v    v        v
        Lambda Action Group Functions
                 |
                 v
        RDS PostgreSQL (supplychain DB)
```

### Key Components

| Layer | Technology |
|---|---|
| Frontend | React + Vite, Recharts, Leaflet, Lucide icons |
| Backend | AWS Lambda (Python 3.12), API Gateway REST, Lambda Function URL |
| AI Agents | AWS Bedrock multi-agent (Supervisor + 4 sub-agents), `claude-sonnet-4-6` |
| Database | AWS RDS PostgreSQL |
| Hosting | S3 + CloudFront (dashboard), Telegram Bot API |
| Forecast | Pickle-based multiplicative seasonal decomposition model |

---

## Project Structure

```
retail_scm_copilot/
├── dashboard/              # React frontend
│   └── src/
│       ├── App.jsx                   # Main shell — sidebar, Sales/Production toggle
│       ├── DashboardTab.jsx          # Sales dashboard (KPIs, charts, dealer table)
│       ├── ProductionDashboardTab.jsx # Production metrics and inventory
│       ├── ChatTab.jsx               # AI copilot chat UI
│       ├── LeafletMap.jsx            # Dealer location map
│       ├── api.js                    # API fetch functions (hardcoded API_BASE)
│       ├── components.jsx            # Shared UI components (KpiCard, etc.)
│       └── data.js                   # Static seed data and chat suggestions
│
├── lambdas/                # AWS Lambda functions
│   ├── dashboard_api/      # 11 REST endpoints for the dashboard
│   ├── telegram_webhook/   # Telegram bot + dashboard chat handler
│   ├── dealer_actions/     # Dealer profile, payments, health scores, entity resolution
│   ├── visit_actions/      # Visit capture, commitment creation, manager alerts
│   ├── order_actions/      # Order capture, inventory check, forecast consumption
│   ├── analytics_actions/  # Manager analytics (team overview, at-risk, pipeline, map)
│   ├── forecast/           # Demand forecast model (pickle-based)
│   └── shared/             # Shared utilities: db_utils.py, telegram_utils.py
│
├── infra/
│   ├── config.py           # All resource IDs, ARNs, agent instructions, action schemas
│   ├── setup.py            # Idempotent deploy script (steps: lambdas, agents, api, etc.)
│   └── state.json          # Persisted resource IDs (Lambda ARNs, agent/alias IDs)
│
├── scripts/
│   ├── train_forecast_model.py   # Trains and serialises the forecast model
│   ├── generate_synthetic_data.py
│   └── validate_data.py
│
└── data/
    └── synthetic/          # Seed CSVs: dealers, products, visits, orders, etc.
```

---

## How It Works

### Telegram Bot Flow
1. Sales rep sends a message to the Telegram bot
2. `scm-telegram-webhook` Lambda receives the webhook
3. Fast-path: `/start` and employee registration are handled immediately (no Bedrock)
4. Slow-path: Lambda fires an **async self-invocation** and returns `200 OK` to Telegram immediately (avoids Telegram's 60s retry timeout)
5. The async invocation enriches the message with role context (REP vs MANAGER), then calls the Bedrock Supervisor Agent
6. Supervisor routes to the appropriate sub-agent (Dealer Intelligence, Visit Capture, Order Planning, or Manager Analytics)
7. Sub-agent invokes Lambda action group functions that query/write PostgreSQL
8. Reply is sent back to the user via Telegram Bot API
9. Session is persisted to PostgreSQL (24h expiry for Telegram, 7d for web)

### Dashboard Chat Flow
1. Manager types a message in the React chat tab
2. Frontend POSTs to the Lambda Function URL (120s timeout)
3. Lambda injects manager context and calls the Bedrock Supervisor
4. Response is returned as buffered JSON and rendered with Markdown

### Dashboard Data Flow
1. React components call API functions in `api.js` on mount
2. Requests go to API Gateway → `scm-dashboard-api` Lambda
3. Lambda runs SQL queries against RDS PostgreSQL and returns JSON
4. Charts render via Recharts; map via Leaflet

### Bedrock Multi-Agent Routing
The Supervisor receives every message and routes it to exactly one sub-agent based on query type:

| Sub-Agent | Handles |
|---|---|
| Dealer Intelligence | Dealer profiles, payment status, visit planning, rep dashboards |
| Visit Capture | Recording field visits, creating commitments, sending alerts |
| Order Planning | Capturing orders, checking inventory, consuming forecasts |
| Manager Analytics | Team KPIs, at-risk dealers, commitment pipeline, production demand/supply |

### Demand Forecast Model
- Algorithm: multiplicative seasonal decomposition + linear trend
- Input: `data/synthetic/weekly_sales_actuals.csv`
- Output: per-product parameters (level, trend, seasonal[1–12], festival boost)
- Serialised as a <2KB pickle — zero ML dependencies on Lambda
- Festival boosts applied for March (Holi) and October (Diwali)

---

## Live URLs

| Resource | URL |
|---|---|
| Dashboard | https://d2glf02xctjq6v.cloudfront.net |
| API Gateway | https://jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod |
| Lambda Function URL | https://gcquxmfbpd7lbty3m4jp7cki6m0xaubd.lambda-url.us-east-1.on.aws/ |

---

## API Endpoints

### Sales
| Method | Path | Description |
|---|---|---|
| GET | `/api/metrics` | KPI cards with month-over-month trend |
| GET | `/api/dealers` | Dealer list with health, revenue, outstanding |
| GET | `/api/revenue-chart` | Monthly revenue / collections / target |
| GET | `/api/commitment-pipeline` | Commitment status breakdown |
| GET | `/api/sales-team` | Sales rep performance table |
| GET | `/api/recent-activity` | Latest visits, orders, alerts feed |
| GET | `/api/weekly-pipeline` | Weekly commitment counts |

### Production
| Method | Path | Description |
|---|---|---|
| GET | `/api/production-metrics` | 6 production KPI cards with trends |
| GET | `/api/production-daily` | Batch-level planned vs actual output |
| GET | `/api/production-demand-supply` | 6-month produced/ordered/committed trend |
| GET | `/api/production-inventory` | Per-product stock, safety stock, days of cover |

### Other
| Method | Path | Description |
|---|---|---|
| GET | `/api/forecast` | Demand forecast (`?product=CLN-500G&weeks=8`) |
| POST | `/api/chat` | AI copilot (API Gateway, 29s limit) |
| POST | Function URL | AI copilot (buffered JSON, 120s limit) |

All Sales endpoints accept an optional `?month=YYYY-MM` query parameter for month filtering.

---

## Setup & Deployment

### Prerequisites
- Python 3.12, Node.js 18+
- AWS CLI configured for account `667736132441`, region `us-east-1`
- A Telegram bot token (set as Lambda environment variable)

### 1. Python environment

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
```

Always use `.venv/Scripts/python` — not system Python.

### 2. Local dashboard development

```bash
cd dashboard
npm install
npm run dev
# http://localhost:5173 — hits the live API Gateway directly
```

### 3. Deploy Lambdas

```bash
.venv/Scripts/python infra/setup.py --step lambdas
```

Packages each Lambda directory with its `shared/` layer and uploads to AWS. Idempotent — safe to re-run.

### 4. Deploy / update Bedrock agents

```bash
.venv/Scripts/python infra/setup.py --step agents
```

Updates agent instructions and action group schemas. The Supervisor alias is refreshed on every run. Sub-agent aliases are NOT auto-refreshed (they cannot be deleted while associated with the Supervisor) — to pick up new sub-agent functions, refresh the sub-agent alias manually in the AWS Console.

### 5. Deploy the dashboard

```bash
.venv/Scripts/python infra/setup.py --step deploy_dashboard
```

Builds the React app (`npm run build`) and syncs to S3 with a CloudFront cache invalidation. First run creates the CloudFront distribution and OAC; subsequent runs reuse the existing distribution from `infra/state.json`.

### 6. Retrain the forecast model

```bash
.venv/Scripts/python scripts/train_forecast_model.py
# Writes lambdas/forecast/forecast_model.pkl
# Then redeploy: .venv/Scripts/python infra/setup.py --step lambdas
```

### All deploy steps

```bash
# Full redeploy (order matters)
.venv/Scripts/python infra/setup.py --step lambdas
.venv/Scripts/python infra/setup.py --step agents
.venv/Scripts/python infra/setup.py --step api
.venv/Scripts/python infra/setup.py --step function_url
.venv/Scripts/python infra/setup.py --step deploy_dashboard
```

---

## Key Infrastructure IDs

| Resource | ID |
|---|---|
| AWS Region / Account | us-east-1 / 667736132441 |
| Bedrock Model | `us.anthropic.claude-sonnet-4-6` |
| Supervisor Agent | CS4Z87AWWT / alias MWVBWEUXUE |
| Dealer Intelligence | HSJZG25AZJ / alias JMQFYHUWTV |
| Visit Capture | JCIET1JRAW / alias IEZJJHMFYV |
| Order Planning | 2BHUYFEBG1 / alias KFGRR9X7BG |
| Manager Analytics | PR3VSGBPTC / alias HZRROIZRKW |
| RDS Host | scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com |
| S3 Bucket | supplychain-copilot-667736132441 |
| CloudFront Dist | E36PHY7L4H1XYK |

---

## Common Gotchas

- **502 errors**: Root cause is usually Supervisor routing to multiple agents or invoking Code Interpreter before routing, causing Lambda timeout. Fix: ensure Supervisor instructions have explicit single-agent routing rules and Lambda timeout >= 120s.
- **SQL LIKE patterns**: Use `%%` (not `%`) in psycopg2 f-strings.
- **Sub-agent alias refresh**: Cannot delete a sub-agent alias while the Supervisor references it. Use the AWS Console to create a new alias for the sub-agent, then re-associate it with the Supervisor.
- **Windows + npm**: `subprocess.run("npm run build", shell=True)` — npm requires `shell=True` on Windows.
- **AWS CLI path mangling in Git Bash**: Prefix commands with `MSYS_NO_PATHCONV=1`.

---

## Author

**Ankan** — [github.com/Ankan54](https://github.com/Ankan54)