# Requirements Document

## Introduction

**SupplyChain Copilot** is an AI-powered sales and production intelligence system designed specifically for Indian MSMEs in B2B distribution (CleanMax brand, detergent distribution, Delhi NCR).

**Problem**: 63 million Indian MSMEs run sales operations on WhatsApp groups, paper notebooks, and Excel spreadsheets. Field intelligence (dealer commitments like "Sharma ji will order 500 units next week") stays trapped in informal conversations and never reaches business planning.

**Solution**: Natural language AI copilot accessible via Telegram (for sales reps) and React dashboard (for managers). Multi-agent system extracts commitments from conversations, tracks fulfillment, and provides actionable intelligence without requiring complex software training.

**Status**: ✅ **FULLY IMPLEMENTED & DEPLOYED** (February 2026)

The system is live on AWS with full PostgreSQL integration, Bedrock Multi-Agent orchestration, and CloudFront-hosted React dashboard. Sales representatives interact via Telegram bot (@CleanMaxSCMBot), while managers access real-time intelligence through the web dashboard.

## Problem Statement

### The Indian MSME Reality

63 million MSMEs power India's distribution network, yet most run their sales operations on informal tools:

**Current State:**
- **WhatsApp is the "ERP"**: Sales reps send messages like "Sir visited Sharma ji, he will order next week" and owners reply "Ok. Collect pending 45000 also"
- **Paper Notebooks (Bahi Khata culture)**: Reps maintain physical visit diaries, manually compiled into Excel at month-end
- **Excel is "Analytics"**: Owners maintain disconnected spreadsheets with no real-time visibility
- **Forecasting = Guesswork**: "Last year same month we did X, so this year X+10%"

**Pain Points:**
- Field intelligence stays in sales rep's head or informal messages
- No real-time visibility into dealer commitments or sales pipeline
- Month-end surprises on sales numbers
- When a sales rep leaves, all dealer relationship knowledge leaves with them
- Multiple visits needed for collections due to poor tracking
- No forward-looking demand signal for inventory planning

### Why Existing Solutions Fail for MSMEs

| Solution | Cost | Why It Fails |
|----------|------|--------------|
| Salesforce | ₹1-2L/month | Budget equals entire IT spend for year |
| SAP Business One | ₹5-10L setup | Overkill, needs dedicated IT team |
| Zoho CRM | ₹20-50K/month | Still requires training and discipline |
| Vyapar/Khatabook | ₹5-10K/month | Accounting focus, not sales operations |

**Real Barriers:**
- Cost sensitivity (even ₹10K/month feels expensive)
- Complexity ("Humara staff seekh nahi payega" - Our staff won't learn)
- Behavior change resistance (reps won't open another app)
- Basic smartphone limitations
- Patchy internet in tier-2/3 markets

## Target Users

### Primary User: Sales Representative

**Profile:**
- Manages 40-60 dealers across a territory
- Makes 8-10 dealer visits per day
- Uses basic Android smartphone
- Comfortable with WhatsApp/Telegram
- May speak Hindi, English, or Hinglish

**Daily Workflow:**
1. Morning: Check which dealers to visit
2. Pre-visit: Remember dealer history and pending issues
3. During visit: Discuss orders, collect payments, note commitments
4. Post-visit: Log visit details (currently in WhatsApp or notebook)
5. Evening: Report to manager

**Pain Points:**
- No quick access to dealer history before visits
- Forgets pending commitments and follow-ups
- Manual visit logging is tedious
- No guidance on which dealers need attention
- No real time visibility to current stock and future production capacity

### Secondary User: Sales Manager / Business Owner

**Profile:**
- Manages 5-15 sales representatives
- Oversees 200-500+ dealers indirectly
- Needs visibility without micromanaging
- Makes inventory and production decisions

**Information Needs:**
- Which dealers have committed to orders (pipeline)
- Which dealers are at risk (declining orders, overdue payments, frustrated due to late delivery)
- Team performance overview
- Collection status
- Forward-looking demand visibility (forecast consumption)
- Alerts for critical situations requiring intervention

## Glossary

### Core System Components

- **SupplyChain_Copilot**: The complete AI system including Telegram bot, agent orchestration, and dashboard
- **Telegram_Bot**: The primary user interface for sales representatives (@CleanMaxSCMBot on Telegram)
- **Supervisor_Agent**: AWS Bedrock routing agent (CS4Z87AWWT) that receives user queries and directs them to appropriate specialized agents
- **Visit_Capture_Agent**: AWS Bedrock agent (JCIET1JRAW) that extracts structured information from natural language visit notes
- **Dealer_Intelligence_Agent**: AWS Bedrock agent (HSJZG25AZJ) that provides information about dealers, payments, orders, and health scores
- **Order_Planning_Agent**: AWS Bedrock agent (2BHUYFEBG1) that handles order processing, inventory checks, and commitment fulfillment tracking
- **Manager_Analytics_Agent**: AWS Bedrock agent (PR3VSGBPTC) that provides company-wide analytics, at-risk dealers, and production demand/supply gap analysis
- **Manager_Dashboard**: React.js web interface (CloudFront-hosted) for sales managers to view team and dealer metrics, forecast consumption, and alerts

### Business Entities

- **Dealer**: A business entity (shop, distributor, retailer) that purchases products for resale
- **Sales_Rep**: A company employee who visits dealers and conducts sales activities
- **Territory**: A geographic region containing multiple dealers assigned to a sales representative
- **Commitment**: A promise made by a dealer regarding future orders (quantity, product, and timeline)
- **Visit**: A record of a sales representative's interaction with a dealer
- **Forecast_Consumption**: The process of matching actual orders against committed/forecasted demand

### Data Types

- **Dealer_Master**: Core dealer information including profile, location, and credit limits
- **Product_Master**: Product catalog with categories and prices
- **Purchase_Order**: An order placed by a dealer for products
- **Invoice**: A bill generated against a delivered order
- **Payment_Record**: Record of payment received against an invoice
- **Visit_Record**: Details of a dealer visit including date, outcome, and notes
- **Commitment_Record**: Extracted commitment from visit notes with product, quantity, and expected date
- **Inventory_Record**: Current stock levels by product and location
- **Data_Pipeline**: The system component responsible for loading and validating synthetic data

## Data Sources

### Structured Data (PostgreSQL RDS)

The system uses PostgreSQL RDS as the primary database with synthetic data representing a typical MSME distributor.

| Data Type | Description | Storage |
|-----------|-------------|---------|
| Dealer Master | Dealer profiles, locations, credit limits | PostgreSQL RDS |
| Product Master | Product catalog (3 SKUs: CLN-500G, CLN-1KG, CLN-2KG) | PostgreSQL RDS |
| Sales Rep Master | Sales team information with Telegram integration | PostgreSQL RDS |
| Territory Master | Geographic assignments (Delhi NCR) | PostgreSQL RDS |
| Historical Orders | Past 6 months of orders | PostgreSQL RDS |
| Historical Invoices | Invoice records with amounts | PostgreSQL RDS |
| Historical Payments | Payment records | PostgreSQL RDS |
| Inventory Levels | Current stock by product and warehouse | PostgreSQL RDS |
| Production Schedule | Manufacturing batches and capacity | PostgreSQL RDS |
| Dealer Health Scores | Time-series health metrics | PostgreSQL RDS |
| Alerts | System-generated notifications | PostgreSQL RDS |
| Sessions | Telegram and web chat sessions | PostgreSQL RDS |

### Unstructured Data (Real-time Capture)

| Source | Data Type | Input Method |
|--------|-----------|--------------|
| Visit Notes | Natural language visit summaries | Telegram chat |
| Commitments | Dealer promises extracted from notes | AI extraction via Visit Capture Agent |
| Follow-ups | Next actions identified from conversation | AI extraction |

## Requirements

### Requirement 1: Natural Language Visit Capture

**User Story:** As a sales representative, I want to log my dealer visits by simply typing what happened in natural language, so that I don't have to fill complex forms.

#### Acceptance Criteria

1. WHEN a sales representative sends a natural language message describing a visit via Telegram, THE Visit_Capture_Agent SHALL extract the dealer name using fuzzy matching
2. WHEN visit notes contain commitment language (e.g., "will order", "promised to buy", "next week order dega"), THE Visit_Capture_Agent SHALL extract commitment details including product, quantity, and expected timeframe
3. WHEN visit notes mention payment collection (e.g., "collected 45K", "payment mila"), THE Visit_Capture_Agent SHALL extract payment amount and method if mentioned
4. WHEN visit notes contain competitor information or complaints, THE Visit_Capture_Agent SHALL extract and categorize these insights
5. WHEN structured information is extracted, THE Visit_Capture_Agent SHALL present a confirmation summary to the user before saving
6. WHEN the user confirms the extracted data, THE SupplyChain_Copilot SHALL store the visit record with all extracted entities linked correctly
7. WHEN entity resolution confidence is below 70%, THE Visit_Capture_Agent SHALL ask for clarification (e.g., "Did you mean Sharma Distributors?")
8. WHEN the user wants to edit extracted data before saving, THE Visit_Capture_Agent SHALL allow corrections via simple responses

### Requirement 2: Dealer Intelligence and Briefing

**User Story:** As a sales representative, I want to get a quick briefing about a dealer before my visit, so that I can have informed conversations.

#### Acceptance Criteria

1. WHEN a user asks for dealer information (e.g., "Brief me for Sharma Distributors", "Sharma ji ka status"), THE Supervisor_Agent SHALL route to the Dealer_Intelligence_Agent
2. WHEN a dealer briefing is requested, THE Dealer_Intelligence_Agent SHALL retrieve and present: basic profile, credit limit, payment status (outstanding amount, overdue days), recent order history (last 3-5 orders), and pending commitments
3. WHEN a dealer has overdue payments, THE Dealer_Intelligence_Agent SHALL highlight this prominently with amount and days overdue
4. WHEN a dealer has unfulfilled commitments approaching their expected date, THE Dealer_Intelligence_Agent SHALL include these in the briefing
5. WHEN dealer health score is below threshold (at-risk), THE Dealer_Intelligence_Agent SHALL flag this with specific reasons
6. WHEN a user asks about payment status specifically (e.g., "Gupta Traders ka payment status"), THE Dealer_Intelligence_Agent SHALL provide detailed payment breakdown

### Requirement 3: Smart Visit Planning

**User Story:** As a sales representative, I want the system to recommend which dealers I should visit today based on priority, so that I can maximize my productivity.

#### Acceptance Criteria

1. WHEN a user requests visit planning (e.g., taps "Plan Day" or asks "Aaj kisko visit karun?"), THE Dealer_Intelligence_Agent SHALL generate a prioritized list of dealers
2. WHEN calculating visit priority, THE Dealer_Intelligence_Agent SHALL consider: payment overdue (collection urgency), days since last order (reorder potential), days since last visit (relationship maintenance), pending commitments about to expire, and dealer health score
3. WHEN presenting the visit plan, THE SupplyChain_Copilot SHALL show dealer name, priority level (high/medium), key reasons for priority, and suggested action
4. WHEN a user requests more details about a recommended dealer, THE SupplyChain_Copilot SHALL provide the full dealer briefing
5. WHEN generating visit plans, THE Dealer_Intelligence_Agent SHALL limit recommendations to a manageable number (4-5 dealers for a day)

### Requirement 4: Sales Dashboard for Representatives

**User Story:** As a sales representative, I want to see my performance summary and alerts, so that I can track my progress.

#### Acceptance Criteria

1. WHEN a user requests dashboard (e.g., taps "Check Status" or asks "Mera situation/status kya hai?"), THE SupplyChain_Copilot SHALL display: sales vs target progress, commitments made and closed count, total collections this month, visit coverage (dealers visited vs total), and pending follow-ups count
2. WHEN displaying progress metrics, THE SupplyChain_Copilot SHALL use visual indicators (progress bars using Unicode characters)
3. WHEN there are urgent items requiring attention, THE SupplyChain_Copilot SHALL show alerts (high-value overdue payments, commitments expiring soon, dealers not visited in 30+ days)
4. WHEN a user asks about specific metrics (e.g., "How much have I collected this month?"), THE Dealer_Intelligence_Agent SHALL provide detailed breakdown

### Requirement 5: Manager Dashboard with Forecast Consumption

**User Story:** As a sales manager, I want to see my team's performance, dealer pipeline, forecast consumption, and production intelligence on a dashboard, so that I can monitor operations and plan inventory.

#### Acceptance Criteria

1. WHEN a manager accesses the dashboard at https://d2glf02xctjq6v.cloudfront.net, THE Manager_Dashboard SHALL display: Sales Tab with revenue metrics, commitment pipeline, at-risk dealers, team performance, and recent activity; Production Tab with production metrics, demand vs supply gap, inventory health, and daily production charts
2. WHEN displaying commitment pipeline, THE Manager_Dashboard SHALL show dealer name, product, quantity, expected date, and status (PENDING/PARTIAL/CONVERTED/MISSED)
3. WHEN displaying at-risk dealers, THE Manager_Dashboard SHALL show dealer name, health status, risk indicators, and assigned sales rep
4. WHEN a manager needs to drill down, THE Manager_Dashboard SHALL allow filtering by month, territory, and dealer category
5. WHEN displaying forecast consumption, THE Manager_Dashboard SHALL show committed quantities vs actual orders received, with backward and forward consumption windows
6. WHEN commitment conversion rate drops below threshold, THE Manager_Dashboard SHALL highlight this for attention
7. WHEN displaying production intelligence, THE Manager_Dashboard SHALL show demand vs supply gap with 8-week forecast horizon, identifying potential shortfalls
8. WHEN displaying the dealer map, THE Manager_Dashboard SHALL use Leaflet with OpenStreetMap tiles, showing dealers with color-coded health status (green/amber/red) and warehouse locations
9. WHEN a manager uses the AI Copilot chat panel, THE Manager_Dashboard SHALL route queries to the Supervisor Agent and display responses with session persistence (7-day expiry)

### Requirement 6: Manager Alerts and Telegram Integration

**User Story:** As a sales manager, I want to receive alerts for critical situations via Telegram and be able to query the system, so that I can intervene when necessary.

#### Acceptance Criteria

1. WHEN a dealer becomes at-risk (health score drops below 50), THE Order_Planning_Agent SHALL generate an alert and send notification to manager's Telegram chat
2. WHEN a commitment due date passes without order, THE Order_Planning_Agent SHALL generate a missed commitment alert for the manager
3. WHEN a discount request exceeds sales rep's authority level (>3%), THE Order_Planning_Agent SHALL route approval request to the manager via Telegram
4. WHEN a dealer complaint is logged by a sales rep, THE Visit_Capture_Agent SHALL generate a high-priority alert and notify the manager immediately via Telegram
5. WHEN a manager receives an alert via Telegram, THE alert SHALL include dealer name, issue description, assigned sales rep, and recommended action
6. WHEN a manager queries the system via Telegram, THE Supervisor_Agent SHALL route to Manager_Analytics_Agent for company-wide queries (team overview, at-risk dealers, production demand/supply)
7. WHEN manager takes action on an alert, THE SupplyChain_Copilot SHALL log the action and update alert status to RESOLVED or DISMISSED

### Requirement 7: Order Planning and Commitment Fulfillment

**User Story:** As a system user, I want the system to track commitment fulfillment and help with order planning, so that I can see which commitments converted to actual orders.

#### Acceptance Criteria

1. WHEN an order is placed by a dealer, THE Order_Planning_Agent SHALL attempt to match it against pending commitments (forecast consumption)
2. WHEN matching orders to commitments, THE Order_Planning_Agent SHALL use backward consumption (match against past commitments first) and forward consumption (match against future commitments if past exhausted) logic
3. WHEN a commitment is partially fulfilled by an order, THE Order_Planning_Agent SHALL update commitment status to show remaining quantity
4. WHEN checking inventory for an order, THE Order_Planning_Agent SHALL verify available-to-promise (ATP) quantity
5. WHEN inventory is insufficient for full order, THE Order_Planning_Agent SHALL suggest order splitting or alternative fulfillment options
6. WHEN commitment due date passes without order, THE Order_Planning_Agent SHALL mark commitment as missed and update dealer reliability score

### Requirement 8: Natural Language Query Processing

**User Story:** As a system user, I want to ask questions in natural language (Hindi, English, or Hinglish), so that I can get information without learning commands.

#### Acceptance Criteria

1. WHEN a user submits a natural language query, THE Supervisor_Agent SHALL classify the intent and determine the appropriate agent to handle it
2. WHEN a query requires information from multiple sources, THE Supervisor_Agent SHALL coordinate requests across agents and combine responses
3. WHEN a query is ambiguous, THE Supervisor_Agent SHALL ask clarifying questions rather than guessing
4. WHEN a query cannot be processed, THE SupplyChain_Copilot SHALL provide helpful suggestions (e.g., "I can help you with dealer info, visit logging, or planning. What would you like?")
5. WHEN processing queries, THE SupplyChain_Copilot SHALL handle common variations and Hinglish phrases (e.g., "payment status" = "payment kya hai" = "kitna baaki hai")

### Requirement 9: Telegram Bot Interface with Registration

**User Story:** As a sales representative or manager, I want to interact with the system through Telegram with automatic registration, so that I can use a familiar interface on my existing phone.

#### Acceptance Criteria

1. WHEN a user starts the bot with `/start` command, THE Telegram_Bot SHALL check if user is registered and display appropriate welcome message
2. WHEN an unregistered user sends `/start`, THE Telegram_Bot SHALL prompt for Employee Code (e.g., EMP002) and auto-register via `register_telegram_user()` function
3. WHEN a registered user types a question, THE Telegram_Bot SHALL route to the Supervisor Agent through Lambda webhook (scm-telegram-webhook)
4. WHEN presenting information, THE Telegram_Bot SHALL use Telegram MarkdownV2 formatting (bold, italic, emojis, tables) via `telegramify-markdown` library
5. WHEN confirmation is needed, THE Telegram_Bot SHALL present inline buttons (e.g., [✓ Save] [✏️ Edit] [❌ Cancel])
6. WHEN the user sends free text instead of tapping buttons, THE Telegram_Bot SHALL process it as a natural language query
7. WHEN the system is processing a Bedrock query, THE Telegram_Bot SHALL use async self-invocation pattern (fire-and-forget) to avoid Telegram's 60s webhook timeout
8. WHEN handling webhook requests, THE Telegram_Bot SHALL verify HMAC secret token via `X-Telegram-Bot-Api-Secret-Token` header
9. WHEN processing messages, THE Telegram_Bot SHALL implement deduplication using `update_id` stored in session context to skip retries
10. WHEN a sales rep query needs user identification, THE Supervisor_Agent SHALL first call `get_sales_rep` with `telegram_user_id` to resolve `sales_person_id`

### Requirement 10: Data Validation and Error Handling

**User Story:** As a system administrator, I want the system to validate data and handle errors gracefully, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN visit data is captured, THE Visit_Capture_Agent SHALL validate that referenced entities (dealer, product) exist or can be resolved
2. WHEN entity resolution fails completely, THE SupplyChain_Copilot SHALL reject the input with a helpful message (e.g., "I couldn't identify the dealer. Please specify the dealer name.")
3. WHEN database operations fail, THE SupplyChain_Copilot SHALL handle exceptions gracefully and inform the user without technical jargon
4. WHEN extracted data contains inconsistencies (e.g., commitment quantity exceeds typical order), THE Visit_Capture_Agent SHALL flag for user confirmation
5. WHEN synthetic data is loaded, THE Data_Pipeline SHALL validate referential integrity across all tables

## Data Scale (Production Deployment)

The system is deployed with synthetic data at the following scale:

| Entity | Count | Notes |
|--------|-------|-------|
| Dealers | 45 | Distributed across Delhi NCR territories |
| Products | 3 | CLN-500G, CLN-1KG, CLN-2KG (CleanMax Detergent) |
| Sales Reps | 5 | Each assigned to territories via territory_assignments |
| Territories | 4 | Delhi NCR regions |
| Historical Orders | ~800 | 6 months of order history (2025-03-28 to 2026-03-05) |
| Historical Visits | ~500 | Visit records with natural language notes |
| Commitments | ~100 | Mix of PENDING, PARTIAL, CONVERTED, and MISSED |
| Inventory Records | 30+ | Current stock by product and warehouse |
| Production Batches | ~200 | Historical and scheduled production |
| Dealer Health Scores | ~8,700 | Time-series health metrics (daily per dealer) |
| Total Database Records | ~8,700 | Across 30+ PostgreSQL tables |

## Scope Definition

### Fully Implemented Features (February 2026)

The following features are fully implemented and deployed on AWS:

**Core Features:**
- Natural language visit capture via Telegram with entity resolution and commitment extraction
- Dealer briefing and intelligence with health scores and payment status
- Smart visit planning with prioritized dealer recommendations
- Sales rep dashboard (Telegram) with performance metrics and alerts
- Manager dashboard (React.js web app at https://d2glf02xctjq6v.cloudfront.net)
- Commitment tracking with forecast consumption (backward/forward logic)
- Manager alerts via Telegram for at-risk situations and complaints
- Order-commitment matching with ATP (Available-to-Promise) inventory checks
- Production intelligence with demand vs supply gap analysis (8-week forecast)
- Interactive dealer map with Leaflet and OpenStreetMap
- AI Copilot chat panel on dashboard with session persistence
- Telegram bot registration flow with Employee Code lookup
- Async webhook pattern to handle Telegram's 60s timeout

**AWS Bedrock Agents (4 Collaborators + 1 Supervisor):**
- Supervisor Agent (CS4Z87AWWT) - Intent classification and routing with Code Interpreter
- Visit Capture Agent (JCIET1JRAW) - NL extraction, entity resolution, commitment creation
- Dealer Intelligence Agent (HSJZG25AZJ) - Profiles, payments, health scores, visit planning, get_sales_rep
- Order Planning Agent (2BHUYFEBG1) - Commitment fulfillment, inventory checks, alerts, forecast consumption
- Manager Analytics Agent (PR3VSGBPTC) - Team overview, at-risk dealers, commitment pipeline, production demand/supply

**Lambda Functions (7 total):**
- scm-telegram-webhook (120s timeout) - Telegram webhook with fast/slow path split
- scm-dashboard-api (29s) - 11 REST endpoints for dashboard
- scm-dealer-actions (29s) - 8 tools for Dealer Intelligence Agent
- scm-visit-actions (29s) - 4 tools for Visit Capture Agent
- scm-order-actions (29s) - 6 tools for Order Planning Agent
- scm-analytics-actions (29s) - 5 tools for Manager Analytics Agent
- scm-forecast (29s) - Demand forecast model (pickle-based)

**Infrastructure:**
- PostgreSQL RDS (scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com)
- API Gateway (jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod)
- CloudFront distribution (d2glf02xctjq6v.cloudfront.net) for React dashboard
- S3 bucket for Lambda deployment packages and dashboard static files
- Telegram webhook (Function URL: gcquxmfbpd7lbty3m4jp7cki6m0xaubd.lambda-url.us-east-1.on.aws/)
- AWS Bedrock inference profile (us.anthropic.claude-sonnet-4-6)

### Future Enhancements (Post-Deployment)

**Near-Term (3 months):**
- WhatsApp Business API integration (currently Telegram)
- Voice input and transcription for visit notes
- Photo capture (shelf images, competitor products, visit selfies)
- GPS tracking of visits with geofencing
- Push notifications for visit reminders

**Long-Term (6-12 months):**
- Advanced demand forecasting with ML (replace pickle model)
- Product recommendation engine based on dealer category
- Route optimization for visit planning (TSP solver)
- Drop sales optimization (identify vans with spare capacity)
- Offline mode with sync capability

**Enterprise Features (Future Market Expansion):**
- Multi-tenant architecture (separate data per company)
- Role-based access control (sales head, regional manager)
- GST compliance and invoice validation
- Integration with external ERP/CRM via APIs
- Audit trails and compliance reporting