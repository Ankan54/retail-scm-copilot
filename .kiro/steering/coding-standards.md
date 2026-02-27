---
inclusion: auto
---

# Coding Standards & Best Practices

## Python Code Standards

### Lambda Handler Pattern
```python
def lambda_handler(event, context):
    """Always use this signature for Lambda entry points."""
    try:
        # Parse input
        body = json.loads(event.get('body', '{}'))
        
        # Business logic
        result = process_request(body)
        
        # Return Bedrock agent format
        return {
            'messageVersion': '1.0',
            'response': {
                'actionGroup': event['actionGroup'],
                'apiPath': event['apiPath'],
                'httpMethod': event['httpMethod'],
                'httpStatusCode': 200,
                'responseBody': {'application/json': {'body': json.dumps(result)}}
            }
        }
    except Exception as e:
        return error_response(str(e))
```

### Database Access Pattern
- **Always use psycopg2 with cursor pattern** (not `conn.execute()`):
```python
import psycopg2
conn = psycopg2.connect(host=..., sslmode='require')
cur = conn.cursor()
cur.execute("SELECT * FROM dealers WHERE dealer_id = %s", (dealer_id,))
rows = cur.fetchall()
```

- **Use `%s` placeholders**, never `?` (SQLite syntax)
- **Always use parameterized queries** to prevent SQL injection
- **Close cursors and connections** in finally blocks or use context managers

### SQL Best Practices

**Pre-aggregate in CTEs to avoid row multiplication**:
```python
# WRONG: Multi-dimensional JOINs cause row explosion
SELECT sp.*, COUNT(o.order_id), COUNT(v.visit_id)
FROM sales_persons sp
LEFT JOIN orders o ON o.sales_person_id = sp.sales_person_id
LEFT JOIN visits v ON v.sales_person_id = sp.sales_person_id
GROUP BY sp.sales_person_id  # This multiplies rows!

# RIGHT: Pre-aggregate each dimension separately
WITH
rep_orders AS (SELECT sales_person_id, COUNT(*) as order_count FROM orders GROUP BY sales_person_id),
rep_visits AS (SELECT sales_person_id, COUNT(*) as visit_count FROM visits GROUP BY sales_person_id)
SELECT sp.*, COALESCE(ro.order_count, 0), COALESCE(rv.visit_count, 0)
FROM sales_persons sp
LEFT JOIN rep_orders ro ON ro.sales_person_id = sp.sales_person_id
LEFT JOIN rep_visits rv ON rv.sales_person_id = sp.sales_person_id
```

**Use `%%` for literal `%` in SQL strings**:
```python
# When building SQL with f-strings or concatenation
query = f"SELECT EXTRACT(WEEK FROM date) %% 4 FROM table"  # %% becomes %
```

**PostgreSQL-specific patterns**:
- `CURRENT_DATE` instead of `date('now')`
- `(date1::date - date2::date)` for date arithmetic
- `STRING_AGG(col, ',')` instead of `GROUP_CONCAT`
- `DISTINCT ON (col) ORDER BY col, date DESC` for "latest row per group"

### Error Handling
- Always wrap Lambda handlers in try-except
- Return structured error responses with meaningful messages
- Log errors to CloudWatch with context
- Never expose database credentials or internal paths in error messages

## JavaScript/React Standards

### Component Structure
- Use functional components with hooks
- Keep components focused and single-purpose
- Extract reusable UI patterns to `components.jsx`

### API Integration Pattern
```javascript
// In api.js - centralize all API calls
export const fetchMetrics = async (month) => {
  const url = month 
    ? `${API_BASE}/api/metrics?month=${month}`
    : `${API_BASE}/api/metrics`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
};

// In component - use custom hook for data fetching
const { data, loading, error } = useApi(() => fetchMetrics(selectedMonth), [selectedMonth]);
```

### Hardcode Configuration for Simplicity
- For single-environment hackathon projects, hardcode API Gateway URLs in `api.js`
- Avoid `.env` files and build-time configuration complexity
- Remove Vite proxy configuration when using hardcoded URLs

## File Organization

### Lambda Functions
- Each action group gets its own directory under `lambdas/`
- Shared utilities go in `lambdas/shared/`
- Include `__init__.py` in all Lambda directories
- Non-Python files (`.pkl`, `.json`) must be bundled in deployment zip

### Infrastructure Code
- All AWS configuration in `infra/config.py`
- Deployment logic in `infra/setup.py`
- Resource IDs tracked in `infra/state.json` (gitignored)

### Scripts
- One-off data scripts go in `scripts/` and should be gitignored if they contain credentials
- Reusable utilities stay in the repo
- Always use `.venv\Scripts\python` on Windows

## Git Hygiene

**Always gitignore**:
- `infra/state.json` (contains resource IDs)
- `*.zip` (Lambda deployment packages)
- One-off migration/debug scripts with hardcoded credentials
- `node_modules/`, `dist/`, `.venv/`
- `__pycache__/`, `*.pyc`

**Acceptable for hackathon** (but not production):
- Hardcoded credentials in `infra/config.py`
- Public RDS security group (0.0.0.0/0)
- No authentication on dashboard

## Windows-Specific Considerations

- Always use `.venv\Scripts\python` not system Python
- Use `sys.stdout.reconfigure(encoding='utf-8')` for Unicode output
- PowerShell command separator is `;` not `&&`
- psycopg2 must be built for Linux (use Lambda Layer, not local pip install)
