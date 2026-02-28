---
inclusion: auto
---

# Bedrock Agents Architecture

## Agent Hierarchy

**Supervisor Agent** (SUPERVISOR mode)
- Agent ID: `CS4Z87AWWT`
- Alias ID: `Z7QHZWIEKT` (prod-v2)
- Model: `us.anthropic.claude-sonnet-4-6` (inference profile)
- Role: Orchestrates four specialized collaborator agents
- Code Interpreter: ENABLED (for complex calculations, weighted averages, compound growth)
- No action groups (delegates all work to collaborators)

**Collaborator Agents**:
1. **Dealer Intelligence Agent** (`HSJZG25AZJ` / `JMQFYHUWTV`)
   - Action Group: `DealerActionGroup` (8 functions)
   - Lambda: `scm-dealer-actions`
   - Capabilities: dealer profiles, payment status, health scores, entity resolution, visit planning, rep dashboard, get_sales_rep

2. **Visit Capture Agent** (`JCIET1JRAW` / `WNY6UJMIGS`)
   - Action Group: `VisitActionGroup` (4 functions)
   - Lambda: `scm-visit-actions`
   - Capabilities: visit logging, commitment creation, entity resolution, recent visits

3. **Order Planning Agent** (`2BHUYFEBG1` / `KFGRR9X7BG`)
   - Action Groups: `OrderActionGroup` (6 functions) + `ForecastActionGroup` (1 function)
   - Lambdas: `scm-order-actions` + `scm-forecast`
   - Capabilities: order processing, inventory checks (ATP), commitment consumption (backward/forward), demand forecasting, alert generation

4. **Manager Analytics Agent** (`PR3VSGBPTC` / `HZRROIZRKW`)
   - Action Group: `ManagerAnalyticsActionGroup` (5 functions)
   - Lambda: `scm-analytics-actions`
   - Capabilities: team overview (all reps), at-risk dealers (network-wide), commitment pipeline (company-wide), dealer map data, production demand/supply gap

## Action Group Function Schemas

All function schemas defined in `infra/config.py` under `AGENT_CONFIGS`.

### Key Constraints

**Maximum 5 parameters per function**: Bedrock enforces this limit. If you need more context:
- Move inferable parameters to Lambda logic (e.g., look up `sales_person_id` from `dealer_id`)
- Use composite parameters (JSON strings)
- Split into multiple function calls

**Parameter types**:
- `string`, `number`, `boolean`, `array`, `object`
- Always include `description` for each parameter (helps agent understand usage)
- Mark required parameters explicitly

### Example Function Schema
```python
{
    "name": "get_dealer_profile",
    "description": "Retrieve detailed profile of a dealer by name, code, or ID",
    "parameters": {
        "dealer_identifier": {
            "description": "Dealer name, code (DLR-XXX), or UUID",
            "type": "string",
            "required": True
        }
    }
}
```

## Lambda Response Format

All Bedrock agent Lambdas must return this structure:
```python
{
    'messageVersion': '1.0',
    'response': {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 200,
        'responseBody': {
            'application/json': {
                'body': json.dumps(result_data)
            }
        }
    }
}
```

**Error responses**:
```python
{
    'messageVersion': '1.0',
    'response': {
        'actionGroup': event['actionGroup'],
        'apiPath': event['apiPath'],
        'httpMethod': event['httpMethod'],
        'httpStatusCode': 400,  # or 500
        'responseBody': {
            'application/json': {
                'body': json.dumps({'error': error_message})
            }
        }
    }
}
```

## Agent Preparation & Deployment

### Update Workflow
1. Modify function schemas in `infra/config.py`
2. Run `python infra/setup.py --step agents`
3. Script automatically:
   - Upserts action groups (safe to run repeatedly)
   - Calls `prepareAgent` API
   - Polls until status = `PREPARED` (10-30 seconds)
   - Creates/updates agent alias
   - Configures supervisor with collaborator ARNs

### Common Issues

**Agent stuck in PREPARING**:
- Wait 30-60 seconds (AWS service delay)
- Check CloudWatch logs for schema validation errors
- Verify Lambda function exists and has correct permissions

**Function not being called**:
- Check function description is clear and specific
- Verify parameter descriptions help agent understand usage
- Test with explicit function name in query: "Use get_dealer_profile for Sharma General Store"

**Parameter validation errors**:
- Ensure required parameters are marked correctly
- Check parameter types match schema
- Verify Lambda handles missing optional parameters

## Entity Resolution Pattern

The `get_sales_rep` function demonstrates fuzzy entity resolution:
```python
def get_sales_rep(identifier):
    """Resolve Telegram username, phone, or name to sales_person_id."""
    # Try exact matches first
    if identifier.startswith('@'):
        # Telegram username
    elif identifier.startswith('+') or identifier.isdigit():
        # Phone number
    else:
        # Fuzzy name match using rapidfuzz
        from rapidfuzz import fuzz
        best_match = max(sales_persons, key=lambda sp: fuzz.ratio(identifier, sp['name']))
```

Use this pattern for any user-facing identifier resolution (dealer names, product names, etc.).

## Testing Agents

### Command-line Testing
```bash
# Single query
.venv\Scripts\python infra/test_agent.py --query "Brief me on Sharma General Store"

# Interactive mode
.venv\Scripts\python infra/test_agent.py --interactive
```

### Test Queries

**English**:
- "Brief me on Sharma General Store"
- "What is the payment status of Gupta Traders?"
- "Which dealers should I visit today? I'm sales rep SP-001"
- "Check inventory for 1kg detergent"

**Hinglish**:
- "Sharma ji ka payment status kya hai?"
- "Aaj mujhe kaun visit karna chahiye?"
- "Met Gupta Traders today. Collected 45K. Will order 2 cases next week."
- "Mera is mahine ka performance kya hai?"

## Agent Instructions

Each agent has detailed instructions in `infra/config.py` under `AGENT_CONFIGS[agent_name]['instruction']`.

**Best practices for instructions**:
- Be specific about when to use each function
- Provide examples of user queries that map to functions
- Explain how to handle ambiguous inputs
- Include business context (e.g., "dealers in Delhi NCR", "detergent products")
- Specify output format preferences (tables, bullet points, etc.)

## Supervisor Configuration

The supervisor uses `collaboratorConfigurations` to route queries to four specialized agents:

```python
{
    'agentDescriptor': {
        'aliasArn': 'arn:aws:bedrock:us-east-1:667736132441:agent-alias/HSJZG25AZJ/JMQFYHUWTV'
    },
    'collaborationInstruction': 'Delegate dealer-related queries (profiles, payments, health scores, visit planning, rep dashboard) to this agent. ALWAYS call get_sales_rep first for Telegram users to resolve sales_person_id.',
    'collaboratorName': 'Dealer_Intelligence_Agent',
    'relayConversationHistory': 'TO_COLLABORATOR'
},
{
    'agentDescriptor': {
        'aliasArn': 'arn:aws:bedrock:us-east-1:667736132441:agent-alias/JCIET1JRAW/WNY6UJMIGS'
    },
    'collaborationInstruction': 'Delegate visit logging and commitment extraction queries to this agent',
    'collaboratorName': 'Visit_Capture_Agent',
    'relayConversationHistory': 'TO_COLLABORATOR'
},
{
    'agentDescriptor': {
        'aliasArn': 'arn:aws:bedrock:us-east-1:667736132441:agent-alias/2BHUYFEBG1/KFGRR9X7BG'
    },
    'collaborationInstruction': 'Delegate order processing, inventory checks, commitment fulfillment, and forecast consumption queries to this agent',
    'collaboratorName': 'Order_Planning_Agent',
    'relayConversationHistory': 'TO_COLLABORATOR'
},
{
    'agentDescriptor': {
        'aliasArn': 'arn:aws:bedrock:us-east-1:667736132441:agent-alias/PR3VSGBPTC/HZRROIZRKW'
    },
    'collaborationInstruction': 'Delegate manager-level queries (team overview, company-wide at-risk dealers, commitment pipeline, production demand/supply gap) to this agent. Use ONLY for [MANAGER DASHBOARD QUERY] context.',
    'collaboratorName': 'Manager_Analytics_Agent',
    'relayConversationHistory': 'TO_COLLABORATOR'
}
```

**Critical Routing Rules**:
1. **[MANAGER DASHBOARD QUERY]** → For company-wide questions, route to Manager_Analytics_Agent. For individual dealer questions, route to Dealer_Intelligence_Agent. NEVER route to both Manager_Analytics_Agent and Order_Planning_Agent.
2. **[SALES REP QUERY]** → FIRST call get_sales_rep with telegram_user_id to resolve sales_person_id. All subsequent calls pass the resolved sales_person_id. NEVER route to Manager_Analytics_Agent.
3. **Code Interpreter Usage** → Only for multi-step calculations (weighted averages, compound growth). DO NOT use before routing. DO NOT use just to check today's date (system context already provides current date).

The supervisor automatically routes based on query content and agent descriptions.
