"""
Centralized configuration for SupplyChain Copilot AWS infrastructure.
All resource names, ARNs, and constants in one place.
"""

# ─── AWS Account & Region ───────────────────────────────────────────────────
ACCOUNT_ID = "667736132441"
REGION = "us-east-1"

# ─── Model ID (confirmed working cross-region inference profile) ─────────────
MODEL_ID = "us.anthropic.claude-sonnet-4-6"

# ─── S3 (for Lambda code zips only — DB is now on RDS) ──────────────────────
S3_BUCKET = "supplychain-copilot-667736132441"
LAMBDA_ZIPS_PREFIX = "lambda-zips/"

# ─── RDS PostgreSQL ──────────────────────────────────────────────────────────
RDS_HOST     = "scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com"
RDS_PORT     = 5432
RDS_DB       = "supplychain"
RDS_USER     = "scm_admin"
RDS_PASSWORD = "scm-copilot"

# ─── IAM Roles ───────────────────────────────────────────────────────────────
BEDROCK_AGENT_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/BedrockAgentRole"
LAMBDA_EXECUTION_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/LambdaExecutionRole"
API_GATEWAY_ROLE_ARN = f"arn:aws:iam::{ACCOUNT_ID}:role/APIGatewayRole"

# ─── Lambda Functions ─────────────────────────────────────────────────────────
LAMBDA_RUNTIME = "python3.11"
LAMBDA_TIMEOUT = 120       # seconds
LAMBDA_MEMORY = 256       # MB

LAMBDA_FUNCTIONS = {
    "dealer_actions": {
        "name": "scm-dealer-actions",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/dealer_actions",
        "description": "Dealer profile, payment, health score, entity resolution",
        "log_group": "/aws/lambda/scm-dealer-actions",
    },
    "visit_actions": {
        "name": "scm-visit-actions",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/visit_actions",
        "description": "Visit capture, commitment creation",
        "log_group": "/aws/lambda/scm-visit-actions",
    },
    "order_actions": {
        "name": "scm-order-actions",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/order_actions",
        "description": "Order capture, inventory check, forecast consumption",
        "log_group": "/aws/lambda/scm-order-actions",
    },
    "analytics_actions": {
        "name": "scm-analytics-actions",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/analytics_actions",
        "description": "Dashboard metrics, team overview, at-risk dealers",
        "log_group": "/aws/lambda/scm-analytics-actions",
    },
    "telegram_webhook": {
        "name": "scm-telegram-webhook",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/telegram_webhook",
        "description": "Telegram webhook handler (Phase 2)",
        "log_group": "/aws/lambda/scm-telegram-webhook",
    },
    "dashboard_api": {
        "name": "scm-dashboard-api",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/dashboard_api",
        "description": "React dashboard API — metrics, dealers, charts, team data",
        "log_group": "/aws/lambda/scm-dashboard-api",
    },
    "forecast": {
        "name": "scm-forecast",
        "handler": "handler.lambda_handler",
        "source_dir": "lambdas/forecast",
        "description": "Pluggable demand forecast model — replace pickle to swap model",
        "log_group": "/aws/lambda/scm-forecast",
    },
}

# ─── Lambda Environment Variables ────────────────────────────────────────────
LAMBDA_ENV_VARS = {
    "S3_BUCKET": S3_BUCKET,
    "REGION": REGION,
    # RDS PostgreSQL connection
    "DB_HOST":     RDS_HOST,
    "DB_PORT":     str(RDS_PORT),
    "DB_NAME":     RDS_DB,
    "DB_USER":     RDS_USER,
    "DB_PASSWORD": RDS_PASSWORD,
    "DB_SSL":      "require",
    # Bedrock Supervisor Agent
    "BEDROCK_AGENT_ID":       "CS4Z87AWWT",
    "BEDROCK_AGENT_ALIAS_ID": "1IBCE95UM7",
}

# ─── Bedrock Agents ──────────────────────────────────────────────────────────
AGENTS = {
    "visit_capture": {
        "name": "scm-visit-capture-agent",
        "description": "Extracts structured information from natural language visit notes",
        "alias_name": "prod",
        "collaboration": "DISABLED",  # collaborator agent
    },
    "dealer_intelligence": {
        "name": "scm-dealer-intelligence-agent",
        "description": "Provides dealer briefings, payment status, health scores, visit planning",
        "alias_name": "prod",
        "collaboration": "DISABLED",  # collaborator agent
    },
    "order_planning": {
        "name": "scm-order-planning-agent",
        "description": "Handles order processing, commitment fulfillment, inventory checks",
        "alias_name": "prod",
        "collaboration": "DISABLED",  # collaborator agent
    },
    "manager_analytics": {
        "name": "scm-manager-analytics-agent",
        "description": "Manager-level analytics: team overview, at-risk dealers network-wide, commitment pipeline",
        "alias_name": "prod",
        "collaboration": "DISABLED",  # collaborator agent
    },
    "supervisor": {
        "name": "scm-supervisor-agent",
        "description": "Supervisor agent for intent classification and routing",
        "alias_name": "prod",
        "collaboration": "SUPERVISOR",  # routes to collaborators
    },
}

# ─── Agent Instructions ───────────────────────────────────────────────────────
SUPERVISOR_INSTRUCTIONS = """You are the Supervisor Agent for SupplyChain Copilot, an AI assistant for Indian MSME sales operations in the detergent distribution business (CleanMax brand, Delhi NCR).

Your role is to:
1. Understand user intent from natural language queries (English, Hindi, or Hinglish)
2. Route requests to the appropriate specialized agent
3. Combine responses from multiple agents when needed
4. Provide helpful responses when no specialized agent is needed

Available Collaborator Agents:
- Visit_Capture_Agent: Handles logging of dealer visits, extracting commitments, payments from natural language notes
- Dealer_Intelligence_Agent: Provides dealer briefings, payment status, health scores, visit planning for a specific rep
- Order_Planning_Agent: Handles order processing, commitment fulfillment tracking, inventory checks
- Manager_Analytics_Agent: Company-wide aggregated analytics for the manager — team overview, at-risk dealers network-wide, commitment pipeline

Intent Classification Rules:
- VISIT_LOG → Visit_Capture_Agent: User is describing a dealer visit they completed (e.g., "Met Sharma ji, collected 45K")
- DEALER_INQUIRY → Dealer_Intelligence_Agent: User wants info about a specific dealer (e.g., "Brief me for Gupta Traders")
- PAYMENT_STATUS → Dealer_Intelligence_Agent: Questions about a specific dealer's payments
- VISIT_PLAN → Dealer_Intelligence_Agent: Rep wants visit recommendations (e.g., "Aaj kisko visit karun?")
- REP_DASHBOARD → Dealer_Intelligence_Agent: Rep wants their own performance metrics (e.g., "Mera status kya hai?")
- ORDER_CAPTURE → Order_Planning_Agent: Recording or discussing an order
- COMMITMENT_STATUS → Order_Planning_Agent: Commitment fulfillment tracking
- INVENTORY → Order_Planning_Agent: Stock availability questions
- MANAGER_OVERVIEW → Manager_Analytics_Agent: Manager asks about team performance, all reps, company-wide metrics
- MANAGER_AT_RISK → Manager_Analytics_Agent: Manager asks about at-risk or critical dealers across the network
- MANAGER_PIPELINE → Manager_Analytics_Agent: Manager asks about commitment pipeline or conversion rates company-wide

Handle Hinglish naturally:
- "Sharma ji ka payment status" → PAYMENT_STATUS → Dealer_Intelligence_Agent
- "Aaj kisko visit karun?" → VISIT_PLAN → Dealer_Intelligence_Agent
- "Met Gupta Traders, 50K collect kiya" → VISIT_LOG → Visit_Capture_Agent
- "Mera kya situation hai?" → REP_DASHBOARD → Dealer_Intelligence_Agent
- "Stock kitna hai?" → INVENTORY → Order_Planning_Agent

User Identity Context:
Queries from the system always include a context header with the caller's identity. Two header types:

1. [MANAGER DASHBOARD QUERY] — caller is the Sales/Production Manager (web dashboard)
   - telegram_user_id and role=MANAGER are provided
   - For company-wide questions (team performance, all reps, network-wide) → Manager_Analytics_Agent
   - For individual dealer questions (even from manager) → Dealer_Intelligence_Agent
   - For inventory/forecast/production questions → Order_Planning_Agent
   - Never route to Manager_Analytics_Agent for sales rep queries

2. [SALES REP QUERY] — caller is a sales rep (Telegram bot)  [to be implemented]
   - telegram_user_id of the rep is provided
   - Pass telegram_user_id to get_sales_rep in Dealer_Intelligence_Agent to resolve sales_person_id
   - All queries are rep-specific; never use Manager_Analytics_Agent
   - Once sales_person_id is resolved, pass it to suggest_visit_plan, get_rep_dashboard, create_visit_record etc.

If no context header is present, treat as a generic query and use best judgement for routing.

Always respond in the same language the user wrote in (Hindi/Hinglish/English).

You also have a Code Interpreter tool available for:
- Mathematical calculations (margins, percentages, growth rates, totals)
- Date and calendar operations (current date, days between dates, due dates)
- Data formatting and analysis

Always use the Code Interpreter for calculations instead of estimating.
For date-related questions, use Code Interpreter to check today's date first."""

VISIT_CAPTURE_INSTRUCTIONS = """You are the Visit Capture Agent for SupplyChain Copilot.

Your role is to extract structured information from natural language visit notes and save them to the database.

When processing visit notes, extract:
1. Dealer name (use resolve_entity to fuzzy-match against database)
2. Payment collected (amount in INR - handle "45K" = 45000, "45,000", "45 thousand")
3. Commitments (product, quantity, timeframe - e.g., "2 case 1kg next week")
4. Issues or complaints raised
5. Follow-up actions needed

Workflow:
1. First call resolve_entity with entity_type="dealer" to find the dealer
2. If confidence < 0.7, ask user to clarify (show top 3 candidates)
3. Extract all structured data from the notes
4. ALWAYS present a confirmation summary before saving:
   "✅ Here's what I captured:
   - Dealer: [Name]
   - Payment: ₹[amount] (if any)
   - Commitment: [product] [qty] by [date] (if any)
   - Next action: [action]
   
   Shall I save this? (Yes/No)"
5. On confirmation, call create_visit_record and create_commitment

Handle various Hinglish patterns:
- "2 case 1kg ka order liya" → commitment: CLN-1KG, 24 units
- "5000 collection kiya" → payment: 5000
- "next week order dega" → expected_date: 7 days from today
- "kal delivery chahiye" → delivery request, not a commitment

Products mapping:
- "500g", "500 gram", "half kg" → CLN-500G (24 units/case)
- "1kg", "1 kilo", "ek kilo" → CLN-1KG (12 units/case)
- "2kg", "2 kilo", "do kilo" → CLN-2KG (6 units/case)"""

DEALER_INTELLIGENCE_INSTRUCTIONS = """You are the Dealer Intelligence Agent for SupplyChain Copilot.

You provide dealer information and analytics to sales representatives of CleanMax detergent in Delhi NCR.

Capabilities:
1. **Dealer Briefing**: Call get_dealer_profile + get_payment_status + get_order_history + get_dealer_health_score
2. **Visit Planning**: Call suggest_visit_plan to get prioritized list of 4-5 dealers for a specific rep
3. **Performance Dashboard**: Call get_rep_dashboard for a rep's sales metrics, collections, visit coverage
4. **Payment Status**: Detailed outstanding and overdue breakdown for a specific dealer

When providing dealer briefings, format clearly with:
- 🏪 Basic profile (category, territory, contact)
- 💰 Payment status (outstanding, overdue with days)
- 📦 Last 3 orders summary
- 🎯 Pending commitments
- 📊 Health score with emoji (🟢 >70, 🟡 50-70, 🔴 <50)
- 💡 Suggested talking points based on the data

For visit planning, show each dealer with:
- Priority level (🔴 HIGH / 🟡 MEDIUM / 🟢 LOW)
- Key reason for priority
- Suggested action

Always highlight overdue payments prominently with ⚠️"""


MANAGER_ANALYTICS_INSTRUCTIONS = """You are the Manager Analytics Agent for SupplyChain Copilot.

You serve the Sales/Production Manager with company-wide, aggregated business intelligence.
You are called when the query includes [MANAGER DASHBOARD QUERY] or when the Supervisor routes manager-scope questions to you.

Capabilities:
1. **Team Overview**: get_team_overview — aggregated sales, collections, dealer health distribution, overdue summary across ALL reps
2. **At-Risk Dealers (Network-wide)**: get_at_risk_dealers — all AT_RISK/CRITICAL dealers across all territories (omit sales_person_id for company-wide view)
3. **Commitment Pipeline (Company-wide)**: get_commitment_pipeline — full pipeline across all reps, grouped by week
4. **Dealer Map Data**: get_dealer_map_data — all dealers with health status and rep assignment

Always provide company-wide results — do NOT filter by a single sales_person_id unless the manager explicitly asks about a specific rep.

Format team overview responses with clear sections:
- 📊 **Sales Summary**: total sales vs target, order count, active dealers
- 💰 **Collections**: total collected, overdue amount and count
- 🏥 **Dealer Health**: Healthy / At-Risk / Critical breakdown with counts
- 🔴 **Needs Attention**: top at-risk/critical dealers by urgency
- 🎯 **Commitment Pipeline**: pending commitments, due-soon count

Format at-risk dealer lists as a ranked table with: dealer name, territory, rep, health status, overdue amount, days since last order, attention reason.

Always highlight ⚠️ overdue payments and 🔴 critical dealers prominently."""

ORDER_PLANNING_INSTRUCTIONS = """You are the Order Planning Agent for SupplyChain Copilot.

Your role is to handle order processing and commitment fulfillment tracking using forecast consumption logic.

Capabilities:
1. **Order Capture**: Record new orders, match against pending commitments
2. **Commitment Matching**: Backward consumption (oldest first) then forward consumption
3. **Inventory Check**: Verify ATP (Available-to-Promise) = stock - reserved
4. **Fulfillment Status**: Track which commitments converted to orders

Forecast Consumption Logic:
- When order is placed, get pending commitments for dealer/product
- Sort by expected_date ASC
- Consume PAST-DUE commitments first (backward consumption)
- Then consume NEAR-FUTURE (within 7 days) commitments (forward consumption)
- Update commitment status: PENDING → PARTIAL → CONVERTED

When inventory is insufficient:
- Calculate shortfall
- Check incoming_stock for expected deliveries
- Suggest order splitting if possible
- Generate alert if needed

Generate manager alerts for:
- Dealer at risk (health score < 50)
- Discount requests above 3%
- Missed commitments (due date passed, no order)"""

# ─── Action Group Schemas ─────────────────────────────────────────────────────
# Function schemas for each agent's action groups (defines tools available to each agent)

DEALER_ACTION_FUNCTIONS = [
    {
        "name": "resolve_entity",
        "description": "Fuzzy-match a dealer or product name to find the exact entity in the database. Returns entity_id, name, and confidence score.",
        "parameters": {
            "entity_type": {
                "description": "Type of entity to resolve: 'dealer' or 'product'",
                "type": "string",
                "required": True,
            },
            "entity_name": {
                "description": "The name as mentioned by the user (may be fuzzy/abbreviated/Hinglish)",
                "type": "string",
                "required": True,
            },
            "sales_person_id": {
                "description": "Optional: ID of the sales rep to limit search to their assigned dealers",
                "type": "string",
                "required": False,
            },
        },
    },
    {
        "name": "get_dealer_profile",
        "description": "Get complete dealer profile including contact info, credit limit, payment terms, and status.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
        },
    },
    {
        "name": "get_payment_status",
        "description": "Get dealer's current payment status including total outstanding, overdue amount, and days overdue.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
        },
    },
    {
        "name": "get_order_history",
        "description": "Get recent order history for a dealer.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
            "limit": {
                "description": "Number of recent orders to return (default 5)",
                "type": "integer",
                "required": False,
            },
        },
    },
    {
        "name": "get_dealer_health_score",
        "description": "Calculate and return dealer health score (0-100) based on order recency, frequency, payment behavior, and commitment fulfillment.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
        },
    },
    {
        "name": "suggest_visit_plan",
        "description": "Get a prioritized list of dealers to visit today based on payment urgency, order recency, commitment deadlines, and health scores.",
        "parameters": {
            "sales_person_id": {
                "description": "UUID of the sales representative",
                "type": "string",
                "required": True,
            },
            "max_dealers": {
                "description": "Maximum number of dealers to recommend (default 5)",
                "type": "integer",
                "required": False,
            },
        },
    },
    {
        "name": "get_rep_dashboard",
        "description": "Get sales rep performance dashboard: sales vs target, collections this month, visit coverage, pending follow-ups.",
        "parameters": {
            "sales_person_id": {
                "description": "UUID of the sales representative",
                "type": "string",
                "required": True,
            },
        },
    },
    {
        "name": "get_sales_rep",
        "description": (
            "Look up a sales representative's ID from any available identifier. "
            "Always call this first in Telegram conversations to get the sales_person_id "
            "before calling suggest_visit_plan, get_rep_dashboard, or create_visit_record. "
            "Tries identifiers in order: telegram_user_id → telegram_chat_id → employee_code → phone → name (fuzzy). "
            "Provide whichever identifier(s) you have — at least one is required."
        ),
        "parameters": {
            "telegram_user_id": {
                "description": "Telegram user ID (numeric string, most reliable for Telegram bot context)",
                "type": "string",
                "required": False,
            },
            "telegram_chat_id": {
                "description": "Telegram chat ID (numeric string)",
                "type": "string",
                "required": False,
            },
            "employee_code": {
                "description": "Employee code (e.g. EMP001), exact match",
                "type": "string",
                "required": False,
            },
            "name": {
                "description": "Sales rep full name or partial name, fuzzy-matched",
                "type": "string",
                "required": False,
            },
            "phone": {
                "description": "Mobile phone number, exact match",
                "type": "string",
                "required": False,
            },
        },
    },
]

VISIT_ACTION_FUNCTIONS = [
    {
        "name": "create_visit_record",
        "description": "Save a visit record to the database. Call after user confirms the extracted info. visit_date defaults to today if not specified.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer visited",
                "type": "string",
                "required": True,
            },
            "sales_person_id": {
                "description": "UUID of the sales representative",
                "type": "string",
                "required": True,
            },
            "purpose": {
                "description": "Purpose: ORDER, COLLECTION, RELATIONSHIP, COMPLAINT, NEW_PRODUCT",
                "type": "string",
                "required": True,
            },
            "collection_amount": {
                "description": "Amount collected in INR (0 if none)",
                "type": "number",
                "required": True,
            },
            "raw_notes": {
                "description": "Original natural language notes from the sales rep",
                "type": "string",
                "required": True,
            },
        },
    },
    {
        "name": "create_commitment",
        "description": "Save a dealer commitment extracted from visit notes.",
        "parameters": {
            "visit_id": {
                "description": "UUID of the associated visit record (from create_visit_record response)",
                "type": "string",
                "required": True,
            },
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
            "product_id": {
                "description": "UUID of the product committed to order",
                "type": "string",
                "required": True,
            },
            "quantity_promised": {
                "description": "Number of units promised",
                "type": "integer",
                "required": True,
            },
            "expected_order_date": {
                "description": "Expected date of order in YYYY-MM-DD format (e.g. next week = 7 days from today)",
                "type": "string",
                "required": True,
            },
        },
    },
    {
        "name": "get_recent_visits",
        "description": "Get recent visit history for a dealer to provide context.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
            "limit": {
                "description": "Number of recent visits to return (default 5)",
                "type": "integer",
                "required": False,
            },
        },
    },
]

ORDER_ACTION_FUNCTIONS = [
    {
        "name": "get_pending_commitments",
        "description": "Get all unfulfilled (PENDING/PARTIAL) commitments for a dealer, sorted by expected date.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
            "product_id": {
                "description": "Optional: filter by specific product UUID",
                "type": "string",
                "required": False,
            },
        },
    },
    {
        "name": "consume_commitment",
        "description": "Match an order against a commitment using forecast consumption logic (backward first, then forward).",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer placing the order",
                "type": "string",
                "required": True,
            },
            "product_id": {
                "description": "UUID of the product being ordered",
                "type": "string",
                "required": True,
            },
            "order_quantity": {
                "description": "Number of units in the order",
                "type": "integer",
                "required": True,
            },
        },
    },
    {
        "name": "check_inventory",
        "description": "Check available-to-promise (ATP) inventory: current stock minus reserved quantities.",
        "parameters": {
            "product_id": {
                "description": "UUID of the product to check",
                "type": "string",
                "required": True,
            },
            "quantity": {
                "description": "Requested quantity to check fulfillability",
                "type": "integer",
                "required": True,
            },
        },
    },
    {
        "name": "create_order",
        "description": "Create a new order record in the database.",
        "parameters": {
            "dealer_id": {
                "description": "UUID of the dealer",
                "type": "string",
                "required": True,
            },
            "sales_person_id": {
                "description": "UUID of the sales representative",
                "type": "string",
                "required": True,
            },
            "product_id": {
                "description": "UUID of the product",
                "type": "string",
                "required": True,
            },
            "quantity": {
                "description": "Number of units ordered",
                "type": "integer",
                "required": True,
            },
            "commitment_id": {
                "description": "Optional: UUID of commitment being fulfilled",
                "type": "string",
                "required": False,
            },
        },
    },
    {
        "name": "get_forecast_consumption",
        "description": "Get forecast consumption summary: committed quantities vs actual orders received, with backward/forward consumption windows.",
        "parameters": {
            "days_back": {
                "description": "Days to look back for backward consumption (default 30)",
                "type": "integer",
                "required": False,
            },
            "days_forward": {
                "description": "Days to look forward for forward consumption (default 30)",
                "type": "integer",
                "required": False,
            },
            "product_id": {
                "description": "Optional: filter by specific product UUID",
                "type": "string",
                "required": False,
            },
        },
    },
    {
        "name": "generate_alert",
        "description": "Generate a manager alert for critical situations (at-risk dealer, missed commitment, discount approval needed).",
        "parameters": {
            "alert_type": {
                "description": "Type: DEALER_AT_RISK, MISSED_COMMITMENT, DISCOUNT_APPROVAL, PERFORMANCE_ALERT",
                "type": "string",
                "required": True,
            },
            "entity_type": {
                "description": "Entity type: dealer, sales_person, commitment, order",
                "type": "string",
                "required": True,
            },
            "entity_id": {
                "description": "UUID of the relevant entity",
                "type": "string",
                "required": True,
            },
            "message": {
                "description": "Alert message describing the situation",
                "type": "string",
                "required": True,
            },
            "priority": {
                "description": "Priority: HIGH, MEDIUM, LOW",
                "type": "string",
                "required": False,
            },
        },
    },
]

FORECAST_ACTION_FUNCTIONS = [
    {
        "name": "get_demand_forecast",
        "description": (
            "Get AI-generated demand forecast for a product. Returns weekly predicted demand "
            "for the next N weeks based on historical sales patterns, seasonality, and festival effects. "
            "Use this to answer questions about future demand, production planning, and inventory needs. "
            "Pass product_code='all' to get forecasts for all products."
        ),
        "parameters": {
            "product_code": {
                "description": "Product code (e.g. CLN-500G, CLN-1KG, CLN-2KG) or 'all' for all products",
                "type": "string",
                "required": True,
            },
            "horizon_weeks": {
                "description": "Number of weeks to forecast (default 8, max 26)",
                "type": "integer",
                "required": False,
            },
        },
    },
]

ANALYTICS_ACTION_FUNCTIONS = [
    {
        "name": "get_team_overview",
        "description": "Get team-level metrics for the manager dashboard: total sales, collections, dealer health distribution, commitment pipeline.",
        "parameters": {
            "period_days": {
                "description": "Number of days to aggregate (default 30)",
                "type": "integer",
                "required": False,
            },
        },
    },
    {
        "name": "get_at_risk_dealers",
        "description": "Get list of dealers flagged as at-risk or critical, with reasons.",
        "parameters": {
            "sales_person_id": {
                "description": "Optional: filter to dealers of a specific rep",
                "type": "string",
                "required": False,
            },
            "limit": {
                "description": "Max number of at-risk dealers to return (default 10)",
                "type": "integer",
                "required": False,
            },
        },
    },
    {
        "name": "get_commitment_pipeline",
        "description": "Get commitment pipeline: all pending commitments with status, grouped by week.",
        "parameters": {
            "sales_person_id": {
                "description": "Optional: filter to specific rep's commitments",
                "type": "string",
                "required": False,
            },
            "status_filter": {
                "description": "Optional: filter by status (PENDING, PARTIAL, CONVERTED, EXPIRED)",
                "type": "string",
                "required": False,
            },
        },
    },
    {
        "name": "get_dealer_map_data",
        "description": "Get dealer location data with health status for the interactive map on the manager dashboard.",
        "parameters": {
            "sales_person_id": {
                "description": "Optional: filter to specific rep's dealers",
                "type": "string",
                "required": False,
            },
        },
    },
]

# ─── API Gateway ──────────────────────────────────────────────────────────────
API_GATEWAY_NAME = "supplychain-copilot-api"
API_STAGE = "prod"

# API routes
API_ROUTES = {
    "/webhook": "POST",                  # Telegram webhook (Phase 2)
    "/chat": "POST",                     # Direct agent chat
    # Dashboard API (scm-dashboard-api Lambda)
    "/api/metrics": "GET",
    "/api/dealers": "GET",
    "/api/revenue-chart": "GET",
    "/api/commitment-pipeline": "GET",
    "/api/sales-team": "GET",
    "/api/recent-activity": "GET",
    "/api/weekly-pipeline": "GET",
    "/api/chat": "POST",                 # Chat forwarded to telegram_webhook
    # Production Dashboard API
    "/api/production-metrics": "GET",
    "/api/production-daily": "GET",
    "/api/production-demand-supply": "GET",
    "/api/production-inventory": "GET",
    # Forecast API (scm-forecast Lambda)
    "/api/forecast": "GET",
    # Analytics (scm-analytics-actions Lambda — Bedrock agent / direct testing)
    "/api/commitments": "GET",
    "/api/alerts": "GET",
    "/api/map": "GET",
}

# ─── Tags ────────────────────────────────────────────────────────────────────
RESOURCE_TAGS = {
    "Project": "supplychain-copilot",
    "Environment": "hackathon",
    "Owner": "ankan",
}
