---
inclusion: auto
---

# SupplyChain Copilot - Project Overview

## What This Project Is

A conversational AI copilot for small MSME detergent manufacturers in Delhi NCR (CleanMax brand). The system helps sales teams manage dealer relationships, track visits, process orders, and monitor supply chain health through natural language interactions (English/Hinglish) via Telegram bot and a React dashboard.

**Status**: ✅ **FULLY DEPLOYED** (February 2026) - Live on AWS with Telegram bot (@CleanMaxSCMBot) and CloudFront-hosted dashboard.

## Live System URLs

| Resource | URL / Identifier |
|---|---|
| **Manager Dashboard** | https://d2glf02xctjq6v.cloudfront.net |
| **API Gateway** | https://jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod |
| **Telegram Webhook** | https://gcquxmfbpd7lbty3m4jp7cki6m0xaubd.lambda-url.us-east-1.on.aws/ |
| **Telegram Bot** | @CleanMaxSCMBot (search in Telegram) |
| **AWS Region** | us-east-1 |
| **Account ID** | 667736132441 |
| **Model** | us.anthropic.claude-sonnet-4-6 (inference profile) |

## Core Architecture

**Multi-Agent System (AWS Bedrock)**:
- Supervisor Agent (CS4Z87AWWT, alias Z7QHZWIEKT) orchestrates four specialized collaborator agents with Code Interpreter enabled
- Dealer Intelligence Agent (HSJZG25AZJ, alias JMQFYHUWTV): dealer profiles, payments, health scores, entity resolution, get_sales_rep (8 tools)
- Visit Capture Agent (JCIET1JRAW, alias WNY6UJMIGS): visit logging, commitment tracking (4 tools)
- Order Planning Agent (2BHUYFEBG1, alias KFGRR9X7BG): order processing, inventory checks, demand forecasting, alerts (6 tools + forecast)
- Manager Analytics Agent (PR3VSGBPTC, alias HZRROIZRKW): team overview, at-risk dealers, commitment pipeline, production demand/supply (5 tools)

**Backend Stack**:
- AWS Lambda (Python 3.11) - 7 functions for all business logic
- PostgreSQL RDS (scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com) as primary database
- API Gateway for REST endpoints (11 dashboard endpoints)
- S3 for Lambda deployment packages and dashboard static files
- Lambda Function URL for Telegram webhook (120s timeout, async pattern)

**Frontend Stack**:
- React + Vite for dashboard UI (CloudFront-hosted)
- Leaflet for interactive dealer maps (OpenStreetMap tiles)
- Chart.js for analytics visualizations (revenue trends, production charts, forecast)
- Direct API Gateway integration (no backend proxy)
- AI Copilot chat panel with session persistence (7-day expiry)

**Telegram Integration**:
- python-telegram-bot library with Lambda Function URL webhook
- telegramify-markdown for MarkdownV2 formatting
- Fast path (sync): /start, registration (no Bedrock, instant response)
- Slow path (async): Bedrock queries (fire-and-forget self-invocation, return 200 immediately)
- Deduplication: update_id stored in session context, skip retries
- HMAC verification via X-Telegram-Bot-Api-Secret-Token header

## Key Business Context

- **Industry**: Small-scale detergent manufacturing (CleanMax brand)
- **Geography**: Delhi NCR only
- **Products**: 3 SKUs (CLN-500G, CLN-1KG, CLN-2KG detergent powder)
- **Users**: Sales representatives (5), sales managers (1)
- **Languages**: English and Hinglish (Hindi-English mix)
- **Data Volume**: ~8,700 records across 30+ PostgreSQL tables
- **Time Range**: 2025-03-28 to 2026-03-05 (shifted for demo)

## Project Status

LIVE on AWS with full PostgreSQL integration. Dashboard fully wired to production API. Telegram bot operational with registration flow and async webhook pattern. All 4 Bedrock collaborator agents deployed with Supervisor orchestration.

## Development Environment

- Python virtual environment: `.venv` (use `.venv\Scripts\python` on Windows)
- Node.js for dashboard: `dashboard/` directory
- All deployment via `infra/setup.py` boto3 script
- Local dashboard dev: `cd dashboard && npm run dev`
- Agent testing: `.venv\Scripts\python infra/test_agent.py --interactive`
