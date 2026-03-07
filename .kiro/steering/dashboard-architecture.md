---
inclusion: auto
---

# Dashboard Architecture

## Tech Stack

**Frontend**:
- React 18 with Vite build tool
- React Leaflet for interactive maps (OpenStreetMap tiles)
- Chart.js for data visualizations
- CSS modules for styling

**Backend**:
- AWS Lambda (`scm-dashboard-api`) with plain Python handler
- API Gateway for REST endpoints
- PostgreSQL (RDS) for data storage

**No middleware**: Frontend calls API Gateway directly (URL hardcoded in `api.js`).

## Dashboard Structure

### Main Components

**App.jsx** - Root component
- Tab navigation (Dashboard, Chat)
- Sales/Production toggle (pill selector in content area)
- State management: `dashView` ('sales' | 'production')

**DashboardTab.jsx** - Sales dashboard
- 6 KPIs with trend indicators
- Interactive dealer map with filters
- Revenue trend chart (monthly bars)
- Commitment pipeline donut chart
- Sales team performance table

**ProductionDashboardTab.jsx** - Production dashboard
- 6 production KPIs with trends
- Batch completion chart (weekly bars)
- Forecast vs actuals chart (line chart with historical + AI forecast)
- Inventory health table

**ChatTab.jsx** - Conversational interface
- Message history sidebar
- Chat input with send button
- Integration with Bedrock supervisor agent (via `scm-telegram-webhook`)

### Reusable Components (components.jsx)

**KpiCard** - Metric display with trend
```jsx
<KpiCard
  title="Total Revenue"
  value="₹12.5L"
  trend={{ text: "+8.3%", up: true }}
  loading={false}
/>
```

**FilterBtn** - Toggle button for filters
```jsx
<FilterBtn
  active={atRiskOnly}
  onClick={() => setAtRiskOnly(!atRiskOnly)}
  label="At-Risk Only"
/>
```

**CTooltip** - Custom tooltip for charts
- Displays on hover with formatted values
- Positioned near cursor

**ComingSoonBtn** - Placeholder for future features
- Disabled button with "Coming Soon" label

## API Integration

### API Base URL
Hardcoded in `dashboard/src/api.js`:
```javascript
const API_BASE = 'https://jn5xaobcs6.execute-api.us-east-1.amazonaws.com/prod';
```

### API Endpoints

**Sales Dashboard**:
- `GET /api/metrics?month=YYYY-MM` - 6 KPIs with trends
- `GET /api/dealers?month=YYYY-MM` - Dealer list with health scores
- `GET /api/revenue-trend?month=YYYY-MM` - Monthly revenue bars
- `GET /api/commitment-pipeline?month=YYYY-MM` - Commitment status breakdown
- `GET /api/sales-team?month=YYYY-MM` - Sales rep performance

**Production Dashboard**:
- `GET /api/production-metrics?month=YYYY-MM` - 6 production KPIs with trends
- `GET /api/batch-completion?month=YYYY-MM` - Weekly batch completion
- `GET /api/forecast?product_id=XXX&weeks=12` - AI forecast + historical actuals
- `GET /api/inventory-health?month=YYYY-MM` - Product inventory status

**Chat**:
- `POST /api/chat` - Send message to Bedrock agent
- `GET /api/sessions` - List chat sessions
- `GET /api/sessions/:id/messages` - Get session history

### Custom Hook Pattern

**useApi** - Data fetching with loading/error states
```javascript
const useApi = (fetchFn, deps = []) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchFn()
      .then(setData)
      .catch(setError)
      .finally(() => setLoading(false));
  }, deps);

  return { data, loading, error };
};

// Usage
const { data, loading, error } = useApi(
  () => fetchMetrics(selectedMonth),
  [selectedMonth]  // Re-fetch when month changes
);
```

## Month Filtering

### Frontend State
```javascript
const [selectedMonth, setSelectedMonth] = useState(null);  // null = current month
```

### Month Selector UI
Pill buttons for recent months:
```jsx
{['2026-02', '2026-01', '2025-12'].map(month => (
  <button
    className={selectedMonth === month ? 'active' : ''}
    onClick={() => setSelectedMonth(month)}
  >
    {formatMonth(month)}
  </button>
))}
```

### Backend Month Range Calculation
```python
def _month_range(month_str):
    """Returns (curr_start, curr_end, prev_start, prev_end) for trend calculation."""
    if not month_str:
        # Current month
        today = date.today()
        curr_start = date(today.year, today.month, 1)
    else:
        # Specified month
        year, month = map(int, month_str.split('-'))
        curr_start = date(year, month, 1)
    
    # Current month end
    _, last_day = calendar.monthrange(curr_start.year, curr_start.month)
    curr_end = date(curr_start.year, curr_start.month, last_day)
    
    # Previous month (for trend)
    prev_end = curr_start - timedelta(days=1)
    prev_start = date(prev_end.year, prev_end.month, 1)
    
    return curr_start, curr_end, prev_start, prev_end
```

### Trend Calculation
```python
# In Lambda response
{
    "total_revenue": 1250000,
    "prev_total_revenue": 1150000,
    # Frontend calculates: ((1250000 - 1150000) / 1150000) * 100 = +8.7%
}
```

## Map Integration

### Leaflet Setup
```jsx
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';

<MapContainer center={[28.6139, 77.2090]} zoom={10}>
  <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
  {dealers.map(dealer => (
    <Marker position={[dealer.latitude, dealer.longitude]}>
      <Popup>
        <strong>{dealer.name}</strong><br/>
        Health: {dealer.health_status}
      </Popup>
    </Marker>
  ))}
</MapContainer>
```

### Map Filters

**At-Risk Only Toggle**:
```javascript
const filteredDealers = atRiskOnly
  ? dealers.filter(d => ['at-risk', 'critical'].includes(d.health_status))
  : dealers;
```

**Category Dropdown**:
```javascript
const filteredDealers = selectedCategory === 'all'
  ? dealers
  : dealers.filter(d => d.category === selectedCategory);
```

## Chart Patterns

### Bar Chart (Revenue Trend)
```javascript
{
  type: 'bar',
  data: {
    labels: ['Jan', 'Feb', 'Mar'],
    datasets: [{
      label: 'Revenue',
      data: [1200000, 1350000, 1250000],
      backgroundColor: '#3b82f6'
    }]
  },
  options: {
    scales: {
      y: {
        ticks: {
          callback: (value) => formatCurrency(value)
        }
      }
    }
  }
}
```

### Donut Chart (Commitment Pipeline)
```javascript
{
  type: 'doughnut',
  data: {
    labels: ['Pending', 'Fulfilled', 'Expired'],
    datasets: [{
      data: [45, 30, 25],
      backgroundColor: ['#fbbf24', '#10b981', '#ef4444']
    }]
  },
  options: {
    plugins: {
      tooltip: {
        callbacks: {
          label: (context) => `${context.label}: ${context.parsed}%`
        }
      }
    }
  }
}
```

### Line Chart (Forecast)
```javascript
{
  type: 'line',
  data: {
    labels: weeks,
    datasets: [
      {
        label: 'Historical',
        data: historicalData,
        borderColor: '#3b82f6',
        borderDash: []  // Solid line
      },
      {
        label: 'AI Forecast',
        data: forecastData,
        borderColor: '#10b981',
        borderDash: [5, 5]  // Dashed line
      }
    ]
  }
}
```

## Styling Conventions

- Use inline styles for dynamic values (colors, widths)
- Use CSS classes for static layout and typography
- Color palette:
  - Primary: `#3b82f6` (blue)
  - Success: `#10b981` (green)
  - Warning: `#fbbf24` (yellow)
  - Danger: `#ef4444` (red)
  - Neutral: `#6b7280` (gray)

## Development Workflow

### Local Development
```bash
cd dashboard
npm run dev
# Opens http://localhost:5173
# Hits live API Gateway (no proxy needed)
```

### Production Build
```bash
cd dashboard
npm run build
# Output: dashboard/dist/
```

### Deployment (TODO)
```bash
# Sync to S3
aws s3 sync dist/ s3://supplychain-copilot-667736132441/dashboard/ --delete

# Invalidate CloudFront
aws cloudfront create-invalidation --distribution-id XXX --paths "/*"
```

## Common Patterns

### Loading States
```jsx
{loading ? (
  <div className="loading">Loading...</div>
) : error ? (
  <div className="error">Error: {error.message}</div>
) : (
  <div className="content">{/* Render data */}</div>
)}
```

### Currency Formatting
```javascript
const formatCurrency = (value) => {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000) return `₹${(value / 100000).toFixed(1)}L`;
  if (value >= 1000) return `₹${(value / 1000).toFixed(1)}K`;
  return `₹${value}`;
};
```

### Trend Indicators
```javascript
const trendPct = (curr, prev) => {
  if (!prev) return { text: 'N/A', up: null };
  const pct = ((curr - prev) / prev) * 100;
  return {
    text: `${pct >= 0 ? '+' : ''}${pct.toFixed(1)}%`,
    up: pct >= 0
  };
};
```
