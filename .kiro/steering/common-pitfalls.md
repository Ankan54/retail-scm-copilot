---
inclusion: auto
---

# Common Pitfalls & Solutions

## Database Issues

### Row Multiplication in Multi-Dimensional JOINs

**Problem**: Joining multiple one-to-many relationships causes row explosion and incorrect aggregates.

**Example of WRONG approach**:
```sql
SELECT sp.sales_person_id, COUNT(o.order_id), COUNT(v.visit_id)
FROM sales_persons sp
LEFT JOIN orders o ON o.sales_person_id = sp.sales_person_id
LEFT JOIN visits v ON v.sales_person_id = sp.sales_person_id
GROUP BY sp.sales_person_id
-- This multiplies: each order × each visit = wrong counts!
```

**Solution**: Pre-aggregate each dimension in CTEs:
```sql
WITH
rep_orders AS (SELECT sales_person_id, COUNT(*) as order_count FROM orders GROUP BY sales_person_id),
rep_visits AS (SELECT sales_person_id, COUNT(*) as visit_count FROM visits GROUP BY sales_person_id)
SELECT sp.*, COALESCE(ro.order_count, 0), COALESCE(rv.visit_count, 0)
FROM sales_persons sp
LEFT JOIN rep_orders ro USING (sales_person_id)
LEFT JOIN rep_visits rv USING (sales_person_id)
```

**Rule**: Any time you need aggregates from multiple tables, pre-aggregate each in a CTE first.

### Schema Drift Between Local and Production

**Problem**: Local reference code (`api_server.py`) has outdated column names that don't match production DB.

**Examples**:
- `alerts.dealer_id` → actually `entity_id` (polymorphic)
- `alerts.severity` → actually `priority`
- `sales_targets.target_amount` → actually `target_value`
- `visits.notes` → actually `raw_notes`

**Solution**: Always validate queries against live DB before assuming column names:
```bash
psql -h scm-postgres.c2na6oc62pb7.us-east-1.rds.amazonaws.com -U scm_admin -d supplychain
\d table_name  # Show table structure
```

**Prevention**: Keep a single source of truth for schema (e.g., `scripts/create_pg_schema.sql`).

### Literal `%` in psycopg2 Queries

**Problem**: Using `%` in SQL (e.g., modulo operator) causes psycopg2 to interpret it as a placeholder.

**Example**:
```python
# WRONG - crashes with "not enough arguments for format string"
query = f"SELECT EXTRACT(WEEK FROM date) % 4 FROM table"
cur.execute(query)

# RIGHT - use %% for literal %
query = f"SELECT EXTRACT(WEEK FROM date) %% 4 FROM table"
cur.execute(query)
```

**Rule**: Use `%%` whenever you need a literal `%` in SQL strings passed to psycopg2.

## AWS Deployment Issues

### psycopg2 Windows Binaries on Lambda

**Problem**: `pip install psycopg2-binary` on Windows installs Windows DLLs that fail on Lambda (Linux).

**Error**: `AttributeError: module 'os' has no attribute 'add_dll_directory'`

**Solution**: Use Lambda Layer with Linux-compatible binaries:
```bash
pip install --platform manylinux2014_x86_64 --target python/ --python-version 3.11 --only-binary=:all: psycopg2-binary
zip -r psycopg2-layer.zip python/
```

**Rule**: Never bundle psycopg2 in Lambda zip on Windows. Always use a Layer built for Linux.

### API Gateway Integration Updates

**Problem**: `put_integration` throws `ConflictException` if integration already exists.

**Solution**: Delete before creating (idempotent pattern):
```python
try:
    client.delete_integration(restApiId=api_id, resourceId=resource_id, httpMethod=method)
except client.exceptions.NotFoundException:
    pass  # Integration doesn't exist yet
client.put_integration(...)
```

**Rule**: Always delete-then-create for API Gateway integrations to handle both new and update cases.

### API Gateway 404 After Route Creation

**Problem**: Routes exist in API Gateway but return 404 when called.

**Cause**: No deployment created after route changes.

**Solution**: Create deployment to `prod` stage:
```bash
aws apigateway create-deployment --rest-api-id jn5xaobcs6 --stage-name prod
```

**Prevention**: `infra/setup.py --step api` does this automatically.

## Bedrock Agent Issues

### Function Not Being Called

**Problem**: Agent doesn't invoke your function even though it seems relevant.

**Causes**:
1. Function description too vague
2. Parameter descriptions unclear
3. Agent doesn't understand when to use it

**Solution**: Make descriptions specific and actionable:
```python
# VAGUE
"description": "Get dealer info"

# SPECIFIC
"description": "Retrieve detailed profile of a dealer including contact info, payment history, and health score. Use when user asks about a specific dealer by name, code, or ID."
```

### Agent Preparation Timeout

**Problem**: Agent status stuck in `PREPARING` for minutes.

**Causes**:
1. Large action group schemas
2. AWS service delays
3. Schema validation errors

**Solution**:
1. Wait 30-60 seconds (normal for complex schemas)
2. Check CloudWatch logs for validation errors
3. Verify Lambda function exists and has correct permissions

### Max 5 Parameters Constraint

**Problem**: Bedrock limits functions to 5 parameters.

**Solutions**:
1. Move inferable params to Lambda logic (look up from related tables)
2. Use composite parameters (JSON strings)
3. Split into multiple function calls

**Example**:
```python
# WRONG - 6 parameters
def create_order(dealer_id, product_id, quantity, sales_person_id, order_date, notes):
    pass

# RIGHT - infer sales_person_id from dealer's territory
def create_order(dealer_id, product_id, quantity, order_date, notes):
    # Look up sales_person_id inside Lambda
    sales_person_id = get_sales_person_for_dealer(dealer_id)
```

## Frontend Issues

### CORS Errors

**Problem**: Browser blocks API requests with CORS error.

**Cause**: Missing CORS headers on API Gateway.

**Solution**: Redeploy API with CORS enabled:
```bash
.venv\Scripts\python infra/setup.py --step api
```

**Prevention**: `infra/setup.py` adds CORS headers automatically to all routes.

### Month Filter Not Applied to All Charts

**Problem**: Some charts show all-time data while others are month-filtered.

**Cause**: Inconsistent filter application in API calls.

**Solution**: Pass month parameter to ALL API endpoints:
```javascript
// WRONG - some calls missing month
fetchMetrics(selectedMonth)
fetchDealers(selectedMonth)
fetchRevenueTrend()  // Missing month!

// RIGHT - all calls include month
fetchMetrics(selectedMonth)
fetchDealers(selectedMonth)
fetchRevenueTrend(selectedMonth)
```

**Rule**: If dashboard has a month filter, ALL API calls must respect it.

### Map Markers Not Updating

**Problem**: Map doesn't re-render when filters change.

**Cause**: React doesn't detect changes in filtered array.

**Solution**: Use key prop to force re-render:
```jsx
<MapContainer key={`${atRiskOnly}-${selectedCategory}`}>
  {/* markers */}
</MapContainer>
```

## Development Workflow Issues

### Windows Unicode Errors

**Problem**: `UnicodeEncodeError` when printing arrows, checkmarks, etc.

**Cause**: Windows PowerShell uses CP1252 encoding.

**Solution**: Reconfigure stdout at script start:
```python
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
```

**Alternative**: Use ASCII-only characters in output.

### Wrong Python Interpreter

**Problem**: Modules not found even though installed in `.venv`.

**Cause**: Using system Python instead of virtual environment.

**Solution**: Always use `.venv\Scripts\python` on Windows:
```bash
# WRONG
python infra/setup.py

# RIGHT
.venv\Scripts\python infra/setup.py
```

### Git Committing Sensitive Files

**Problem**: Accidentally committing credentials, deployment zips, or one-off scripts.

**Prevention**: Update `.gitignore`:
```
# Deployment artifacts
infra/state.json
*.zip

# One-off scripts with credentials
scripts/migrate_*.py
scripts/shift_dates.py

# Python
__pycache__/
*.pyc
.venv/

# Node
node_modules/
dist/
```

**Rule**: Review `git status` before every commit. If you see unexpected files, add them to `.gitignore`.

## Testing Issues

### SQL Query Timeout

**Problem**: Lambda times out after 120 seconds.

**Cause**: Inefficient query with row multiplication or missing indexes.

**Solution**:
1. Check for multi-dimensional JOINs (use CTEs)
2. Add indexes on frequently joined columns
3. Use `EXPLAIN ANALYZE` to identify slow parts

**Example**:
```sql
EXPLAIN ANALYZE
SELECT ...
-- Look for "Seq Scan" on large tables (add index)
-- Look for high row counts in intermediate steps (refactor query)
```

### Forecast Model Not Loading

**Problem**: Lambda can't find `forecast_model.pkl`.

**Cause**: Non-Python files not included in deployment zip.

**Solution**: Ensure `infra/setup.py` bundles all files in Lambda directory:
```python
# In setup.py
for root, dirs, files in os.walk(source_dir):
    for file in files:
        # Include ALL files, not just .py
        zip_file.write(file_path, arcname=relative_path)
```

**Rule**: Always test Lambda locally with the actual zip contents before deploying.


## Telegram Integration Issues

### Webhook Timeout

**Problem**: Telegram has 60s webhook timeout. Bedrock calls take 50-60s. If Lambda processes synchronously, Telegram retries and user gets duplicate responses.

**Solution**: Async self-invocation pattern (implemented in `lambdas/telegram_webhook/handler.py`):
1. Validate webhook secret token (X-Telegram-Bot-Api-Secret-Token header)
2. Try **fast path first** (`_handle_telegram_fast`) — /start, registration (no Bedrock, instant response)
3. If needs Bedrock → fire-and-forget async (`InvocationType='Event'`), return 200 immediately
4. Async handler (`_handle_telegram_bedrock`) processes Bedrock query
5. **Deduplication**: Store `update_id` in session context, skip if already processed (Lambda Event retries up to 2x on failure)
6. **Markdown Formatting**: `telegramify-markdown` library converts AI output (`**bold**`, tables, lists) → Telegram MarkdownV2
7. **Session Persistence**: `sessions` table (24-hour expiry for Telegram, 7-day for web)

**Lambda Function URL**: https://gcquxmfbpd7lbty3m4jp7cki6m0xaubd.lambda-url.us-east-1.on.aws/
**Timeout**: 120s (allows async invocation to complete)

### 502 Errors from Supervisor

**Problem**: Supervisor using Code Interpreter before routing + calling multiple agents → hits Lambda timeout → 502.

**Fix**:
1. Lambda timeout ≥ 120s (set in config.py)
2. Supervisor instructions: **DO NOT use Code Interpreter before routing** — route first, calculate from returned data if needed
3. Clear single-agent routing rules per query type (never route to both Manager_Analytics + Order_Planning)

### Markdown Formatting Errors

**Problem**: Telegram rejects messages with invalid MarkdownV2 syntax (unescaped special characters).

**Cause**: Agent output contains special characters (_, *, [, ], (, ), ~, `, >, #, +, -, =, |, {, }, ., !) that need escaping in MarkdownV2.

**Solution**: Use `telegramify-markdown` library to convert standard markdown to Telegram MarkdownV2:
```python
from telegramify_markdown import markdownify
formatted_text = markdownify(agent_response)
```

**Rule**: Always use `telegramify-markdown` for agent responses sent to Telegram. Never send raw markdown.
