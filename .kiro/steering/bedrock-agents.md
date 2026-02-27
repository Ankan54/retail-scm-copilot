---
inclusion: auto
---

# Bedrock Agents Architecture

## Agent Hierarchy

**Supervisor Agent** (SUPERVISOR mode)
- Agent ID: `CS4Z87AWWT`
- Alias ID: `1IBCE95UM7`
- Model: `us.anthropic.claude-sonnet-4-6`
- Role: Orchestrates three specialized collaborator agents
- No action groups (delegates all work to collaborators)

**Collaborator Agents**:
1. **Dealer Intelligence Agent** (`HSJZG25AZJ` / `BVJNNOTHHG`)
   - Action Group: `DealerActionGroup` (9 functions)
   - Lambda: `scm-dealer-actions`
   - Capabilities: dealer profiles, payment status, health scores, entity resolution

2. **Visit Capture Agent** (`JCIET1JRAW` / `WNY6UJMIGS`)
   - Action Group: `VisitActionGroup`
   - Lambda: `scm-visit-actions`
   - Capabilities: visit logging, commitment creation

3. **Order Planning Agent** (`2BHUYFEBG1` / `KFGRR9X7BG`)
   - Action Groups: `OrderActionGroup` + `ForecastActionGroup`
   - Lambdas: `scm-order-actions` + `scm-forecast`
   - Capabilities: order processing, inventory checks, demand forecasting

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

The supervisor uses `collaboratorConfigurations` to route queries:
```python
{
    'agentDescriptor': {
        'aliasArn': 'arn:aws:bedrock:us-east-1:667736132441:agent-alias/HSJZG25AZJ/BVJNNOTHHG'
    },
    'collaborationInstruction': 'Delegate dealer-related queries to this agent',
    'collaboratorName': 'Dealer_Intelligence_Agent',
    'relayConversationHistory': 'TO_COLLABORATOR'
}
```

The supervisor automatically routes based on query content and agent descriptions.
