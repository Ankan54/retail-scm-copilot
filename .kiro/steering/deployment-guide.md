---
inclusion: auto
---

# Deployment Guide

## Prerequisites

- AWS CLI configured with credentials for account 667736132441
- Python 3.11 with virtual environment at `.venv`
- Node.js and npm for dashboard builds
- PostgreSQL client (optional, for direct DB access)

## Deployment Commands

All deployments use `infra/setup.py` with step flags:

### Deploy Lambda Functions
```bash
.venv\Scripts\python infra/setup.py --step lambdas
```
Run this after any code changes in `lambdas/` directories.

**What it does**:
- Creates psycopg2 Lambda Layer (Linux-compatible binaries)
- Zips each Lambda function with dependencies (7 functions total)
- Uploads zips to S3
- Updates Lambda function code
- Attaches psycopg2 layer to all functions
- Includes forecast model pickle file in scm-forecast deployment

**Lambda Functions Deployed**:
- scm-telegram-webhook (120s timeout) - Telegram webhook with fast/slow path split
- scm-dashboard-api (29s) - 11 REST endpoints for dashboard
- scm-dealer-actions (29s) - 8 tools for Dealer Intelligence Agent
- scm-visit-actions (29s) - 4 tools for Visit Capture Agent
- scm-order-actions (29s) - 6 tools for Order Planning Agent
- scm-analytics-actions (29s) - 5 tools for Manager Analytics Agent
- scm-forecast (29s) - Demand forecast model (pickle-based)

### Update Bedrock Agent Action Groups
```bash
.venv\Scripts\python infra/setup.py --step agents
```
Run this after changes to function schemas in `infra/config.py`.

**What it does**:
- Upserts action groups (safe to run repeatedly)
- Calls `prepareAgent` and waits for PREPARED status
- Creates/updates agent aliases
- Configures supervisor with collaborator ARNs

### Deploy Dashboard to CloudFront
```bash
.venv\Scripts\python infra/setup.py --step deploy_dashboard
```
Run this after dashboard code changes or first-time setup.

**What it does**:
- Builds React dashboard (`npm run build` in dashboard/)
- Creates S3 bucket if not exists (supplychain-copilot-667736132441)
- Creates CloudFront distribution with OAC (Origin Access Control) if not exists
- Syncs dist/ files to S3 with appropriate cache headers:
  - index.html: no-store (always fresh)
  - assets/*: immutable 1yr (content-hashed by Vite)
  - others: 1 day cache
- Creates CloudFront invalidation to clear cache
- Updates state.json with distribution ID

**First run**: Creates OAC + distribution + S3 bucket policy
**Subsequent runs**: Reuses dist from state.json, syncs files + creates invalidation
**OriginPath**: /dashboard strips prefix so browser paths match Vite's base: "/" output

**Dashboard URL**: https://d2glf02xctjq6v.cloudfront.net

### Full Redeploy
```bash
.venv\Scripts\python infra/setup.py
```
Runs all steps in sequence. Use for initial setup or major changes.

## Retrain Forecast Model

After new sales data arrives:
```bash
.venv\Scripts\python scripts/train_forecast_model.py
```

This regenerates `lambdas/forecast/forecast_model.pkl`. Then redeploy lambdas:
```bash
.venv\Scripts\python infra/setup.py --step lambdas
```

## Dashboard Deployment

### Local Development
```bash
cd dashboard
npm run dev
```
Hits live API Gateway directly (URL hardcoded in `api.js`): https://jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod

### Production Build
```bash
cd dashboard
npm run build
```
Output: `dashboard/dist/` directory.

### Deploy to CloudFront
```bash
.venv\Scripts\python infra/setup.py --step deploy_dashboard
```

This command:
1. Builds dashboard with `npm run build`
2. Syncs dist/ to S3 bucket (supplychain-copilot-667736132441)
3. Creates CloudFront invalidation to clear cache
4. Dashboard available at: https://d2glf02xctjq6v.cloudfront.net

**CloudFront Configuration**:
- Origin: S3 bucket with OAC (Origin Access Control)
- OriginPath: /dashboard (strips prefix for Vite routing)
- Error pages: 403/404 → /index.html (for SPA routing)
- Cache: index.html = no-store, assets/* = immutable 1yr, others = 1 day
- No authentication (hackathon/demo only)

## Testing Deployments

### Test Bedrock Agents
```bash
# Single query
.venv\Scripts\python infra/test_agent.py --query "Brief me on Sharma General Store"

# Interactive mode
.venv\Scripts\python infra/test_agent.py --interactive
```

### Validate Dashboard API
```bash
.venv\Scripts\python scripts/validate_dashboard_api.py
```
Tests all 11 endpoints without requiring credentials.

### Check Database
```bash
psql -h scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com -U scm_admin -d supplychain
# Password: scm-copilot
```

## Common Deployment Issues

### psycopg2 Import Error on Lambda
**Symptom**: `os.add_dll_directory` AttributeError
**Cause**: Windows-native psycopg2 binaries in Lambda zip
**Fix**: Ensure psycopg2 is only in the Lambda Layer, not bundled in function zip

### API Gateway 404 After Route Creation
**Symptom**: Routes exist but return 404
**Cause**: No deployment created after route changes
**Fix**: Run `aws apigateway create-deployment` or use `--step api`

### Agent Preparation Timeout
**Symptom**: Agent status stuck in PREPARING
**Cause**: Large action group schemas or AWS service delays
**Fix**: Wait 30-60 seconds, check CloudWatch logs for errors

### SQL Query Timeout
**Symptom**: Lambda timeout after 120 seconds
**Cause**: Row multiplication from multi-dimensional JOINs
**Fix**: Refactor query to use CTEs with pre-aggregation (see coding-standards.md)

### Dashboard CORS Error
**Symptom**: Browser blocks API requests
**Cause**: Missing CORS headers on API Gateway
**Fix**: Redeploy API with `--step api` (adds CORS automatically)

## Resource Cleanup

To delete all AWS resources (use with caution):
```bash
# Delete Lambda functions
aws lambda delete-function --function-name scm-dealer-actions
# ... repeat for all functions

# Delete Bedrock agents
aws bedrock-agent delete-agent --agent-id CS4Z87AWWT

# Delete API Gateway
aws apigateway delete-rest-api --rest-api-id jn5xaobcs6

# Delete RDS instance (takes ~10 minutes)
aws rds delete-db-instance --db-instance-identifier scm-postgres --skip-final-snapshot
```

**Note**: S3 bucket and IAM roles are shared resources - do not delete unless certain.
