---
inclusion: auto
---

# SupplyChain Copilot - Project Overview

## What This Project Is

A conversational AI copilot for small MSME detergent manufacturers in Delhi NCR. The system helps sales teams manage dealer relationships, track visits, process orders, and monitor supply chain health through natural language interactions (English/Hinglish) and a React dashboard.

## Core Architecture

**Multi-Agent System (AWS Bedrock)**:
- Supervisor Agent (SUPERVISOR mode) orchestrates three specialized collaborator agents
- Dealer Intelligence Agent: dealer profiles, payments, health scores, entity resolution
- Visit Capture Agent: visit logging, commitment tracking
- Order Planning Agent: order processing, inventory checks, demand forecasting

**Backend Stack**:
- AWS Lambda (Python 3.11) for all business logic
- PostgreSQL (RDS) as primary database
- API Gateway for REST endpoints
- S3 for Lambda deployment packages

**Frontend Stack**:
- React + Vite for dashboard UI
- Leaflet for interactive dealer maps
- Chart.js for analytics visualizations
- Direct API Gateway integration (no backend proxy)

## Key Business Context

- **Industry**: Small-scale detergent manufacturing
- **Geography**: Delhi NCR only
- **Products**: 3 SKUs (500g, 1kg, 2kg CleanMax Detergent)
- **Users**: Sales representatives, sales managers
- **Languages**: English and Hinglish (Hindi-English mix)
- **Data Volume**: ~8,700 records across 30+ tables

## Project Status

LIVE on AWS with full PostgreSQL integration. Dashboard fully wired to production API. Telegram integration planned for Phase 2.

## Development Environment

- Python virtual environment: `.venv` (use `.venv\Scripts\python` on Windows)
- Node.js for dashboard: `dashboard/` directory
- All deployment via `infra/setup.py` boto3 script
- Local dashboard dev: `cd dashboard && npm run dev`
