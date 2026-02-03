# Requirements Document

## Introduction

The SupplyChain Copilot is an AI-powered assistant designed specifically for Indian MSMEs (Micro, Small, and Medium Enterprises) in the B2B distribution and retail supply chain sector. Unlike large enterprises that use sophisticated ERP systems like SAP or Salesforce, Indian MSMEs typically operate using WhatsApp groups, Excel spreadsheets, and paper notebooks. Field intelligence from sales representatives—such as dealer commitments like "Sharma ji will order 500 units next week"—remains trapped in informal conversations and never reaches business planning.

The system captures sales visit data through natural language conversations on Telegram, automatically extracts dealer commitments, and combines them with transactional history to provide actionable intelligence. Multiple specialized AI agents work together to help sales representatives prepare for dealer visits, plan their day efficiently, and give business owners visibility into their sales pipeline without requiring complex software training.

The platform is designed for accessibility: it works on basic smartphones, requires no training (conversational interface), and integrates with tools Indian MSMEs already use (Telegram/WhatsApp).

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

### Secondary User: Sales Manager / Business Owner

**Profile:**
- Manages 5-15 sales representatives
- Oversees 200-500+ dealers indirectly
- Needs visibility without micromanaging
- Makes inventory and production decisions

**Information Needs:**
- Which dealers have committed to orders (pipeline)
- Which dealers are at risk (declining orders, overdue payments)
- Team performance overview
- Collection status

## Glossary

### Core System Components

- **SupplyChain_Copilot**: The complete AI system including Telegram bot, agent orchestration, and dashboard
- **Telegram_Bot**: The primary user interface for sales representatives to interact with the system
- **Supervisor_Agent**: The routing agent that receives user queries and directs them to appropriate specialized agents
- **Visit_Capture_Agent**: The agent that extracts structured information from natural language visit notes
- **Dealer_Intelligence_Agent**: The agent that provides information about dealers, payments, orders, and health scores
- **Manager_Dashboard**: Simple web interface (Streamlit) for sales managers to view team and dealer metrics

### Business Entities

- **Dealer**: A business entity (shop, distributor, retailer) that purchases products for resale
- **Sales_Rep**: A company employee who visits dealers and conducts sales activities
- **Territory**: A geographic region containing multiple dealers assigned to a sales representative
- **Commitment**: A promise made by a dealer regarding future orders (quantity, product, and timeline)
- **Visit**: A record of a sales representative's interaction with a dealer

### Data Types

- **Dealer_Master**: Core dealer information including profile, location, and credit limits
- **Product_Master**: Product catalog with categories and prices
- **Purchase_Order**: An order placed by a dealer for products
- **Invoice**: A bill generated against a delivered order
- **Payment_Record**: Record of payment received against an invoice
- **Visit_Record**: Details of a dealer visit including date, outcome, and notes
- **Commitment_Record**: Extracted commitment from visit notes with product, quantity, and expected date

## Data Sources

### Structured Data (Initial Load)

For the hackathon, synthetic data will be generated to simulate a typical MSME distributor.

| Data Type | Description | Format |
|-----------|-------------|--------|
| Dealer Master | Dealer profiles, locations, credit limits | CSV/SQLite |
| Product Master | Product catalog, categories, prices | CSV/SQLite |
| Sales Rep Master | Sales team information | CSV/SQLite |
| Territory Master | Geographic assignments | CSV/SQLite |
| Historical Orders | Past 6 months of orders | CSV/SQLite |
| Historical Invoices | Invoice records with amounts | CSV/SQLite |
| Historical Payments | Payment records | CSV/SQLite |

### Unstructured Data (Real-time Capture)

| Source | Data Type | Input Method |
|--------|-----------|--------------|
| Visit Notes | Natural language visit summaries | Telegram chat |
| Commitments | Dealer promises extracted from notes | AI extraction |
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
5. WHEN generating visit plans, THE Dealer_Intelligence_Agent SHALL limit recommendations to a manageable number (5-8 dealers for a day)

### Requirement 4: Sales Dashboard for Representatives

**User Story:** As a sales representative, I want to see my performance summary and alerts, so that I can track my progress.

#### Acceptance Criteria

1. WHEN a user requests dashboard (e.g., taps "Dashboard" or asks "Mera status kya hai?"), THE SupplyChain_Copilot SHALL display: sales vs target progress, total collections this month, visit coverage (dealers visited vs total), and pending follow-ups count
2. WHEN displaying progress metrics, THE SupplyChain_Copilot SHALL use visual indicators (progress bars using Unicode characters)
3. WHEN there are urgent items requiring attention, THE SupplyChain_Copilot SHALL show alerts (high-value overdue payments, commitments expiring soon, dealers not visited in 30+ days)
4. WHEN a user asks about specific metrics (e.g., "How much have I collected this month?"), THE Dealer_Intelligence_Agent SHALL provide detailed breakdown

### Requirement 5: Manager Dashboard

**User Story:** As a sales manager, I want to see my team's performance and dealer pipeline on a simple dashboard, so that I can monitor operations without calling each rep.

#### Acceptance Criteria

1. WHEN a manager accesses the dashboard, THE Manager_Dashboard SHALL display: commitment pipeline (all pending commitments with status), at-risk dealers list (declining orders, overdue payments), team performance summary, and collection status
2. WHEN displaying commitment pipeline, THE Manager_Dashboard SHALL show dealer name, product, quantity, expected date, and status (new/due soon/overdue)
3. WHEN displaying at-risk dealers, THE Manager_Dashboard SHALL show dealer name, risk indicators, and assigned sales rep
4. WHEN a manager needs to drill down, THE Manager_Dashboard SHALL allow filtering by sales rep, territory, or time period

### Requirement 6: Natural Language Query Processing

**User Story:** As a system user, I want to ask questions in natural language (Hindi, English, or Hinglish), so that I can get information without learning commands.

#### Acceptance Criteria

1. WHEN a user submits a natural language query, THE Supervisor_Agent SHALL classify the intent and determine the appropriate agent to handle it
2. WHEN a query requires information from multiple sources, THE Supervisor_Agent SHALL coordinate requests across agents and combine responses
3. WHEN a query is ambiguous, THE Supervisor_Agent SHALL ask clarifying questions rather than guessing
4. WHEN a query cannot be processed, THE SupplyChain_Copilot SHALL provide helpful suggestions (e.g., "I can help you with dealer info, visit logging, or planning. What would you like?")
5. WHEN processing queries, THE SupplyChain_Copilot SHALL handle common variations and Hinglish phrases (e.g., "payment status" = "payment kya hai" = "kitna baaki hai")

### Requirement 7: Telegram Bot Interface

**User Story:** As a sales representative, I want to interact with the system through Telegram, so that I can use a familiar interface on my existing phone.

#### Acceptance Criteria

1. WHEN a user starts the bot, THE Telegram_Bot SHALL display a main menu with primary actions: Log Visit, Plan Day, Dashboard, and Help
2. WHEN a user taps a menu button, THE Telegram_Bot SHALL initiate the corresponding flow
3. WHEN presenting information, THE Telegram_Bot SHALL use Telegram-compatible formatting (bold, italic, emojis, inline keyboards)
4. WHEN confirmation is needed, THE Telegram_Bot SHALL present inline buttons (e.g., [✓ Save] [✏️ Edit] [❌ Cancel])
5. WHEN the user sends free text instead of tapping buttons, THE Telegram_Bot SHALL process it as a natural language query
6. WHEN the system is processing, THE Telegram_Bot SHALL show appropriate feedback (typing indicator or progress message)

### Requirement 8: Data Validation and Error Handling

**User Story:** As a system administrator, I want the system to validate data and handle errors gracefully, so that data integrity is maintained.

#### Acceptance Criteria

1. WHEN visit data is captured, THE Visit_Capture_Agent SHALL validate that referenced entities (dealer, product) exist or can be resolved
2. WHEN entity resolution fails completely, THE SupplyChain_Copilot SHALL reject the input with a helpful message (e.g., "I couldn't identify the dealer. Please specify the dealer name.")
3. WHEN database operations fail, THE SupplyChain_Copilot SHALL handle exceptions gracefully and inform the user without technical jargon
4. WHEN extracted data contains inconsistencies (e.g., commitment quantity exceeds typical order), THE Visit_Capture_Agent SHALL flag for user confirmation
5. WHEN synthetic data is loaded, THE Data_Pipeline SHALL validate referential integrity across all tables

## Data Scale (Hackathon Scope)

For the hackathon demonstration, the system will use synthetic data at the following scale:

| Entity | Count | Notes |
|--------|-------|-------|
| Dealers | 50-80 | Distributed across 3-4 territories |
| Products | 20-30 | Across 4-5 categories |
| Sales Reps | 5-8 | Each assigned to 1-2 territories |
| Territories | 3-4 | Geographic regions |
| Historical Orders | 500-800 | 6 months of order history |
| Historical Visits | 300-500 | Visit records with notes |
| Commitments | 50-100 | Mix of fulfilled, pending, and missed |

## Out of Scope for Hackathon

The following features are identified for future development and are not part of the current hackathon build:

### Future Enhancements (Post-Hackathon)
- WhatsApp Business API integration (currently using Telegram for ease of development)
- Voice input and transcription for visit notes
- Regional language support (Hindi, Tamil, etc.) beyond basic Hinglish
- Offline mode with sync capability
- Push notifications for reminders and alerts
- Advanced demand forecasting with ML models
- Product recommendation engine
- Route optimization for visit planning
- Photo capture (shelf images, competitor products)
- GPS tracking of visits

### Enterprise Features (Not Target Market)
- Integration with external ERP/CRM systems via live APIs
- GST compliance and invoice validation
- Multi-company/multi-tenant architecture
- Role-based access control beyond manager/rep
- Audit trails and compliance reporting
- Custom report generation with PDF export

### Dealer-Side Features (Future Extension)
- Dealer self-service portal
- Inventory tracking for dealers
- Automated reorder recommendations
- Payment gateway integration
- Order placement via chatbot