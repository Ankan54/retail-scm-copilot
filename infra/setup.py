#!/usr/bin/env python3
"""
SupplyChain Copilot - Infrastructure Setup Script
Run this to deploy all AWS resources. Safe to re-run (idempotent).

Usage:
    python infra/setup.py                    # Full setup
    python infra/setup.py --step upload_db   # Just upload DB
    python infra/setup.py --step lambdas     # Just package + deploy Lambdas
    python infra/setup.py --step agents      # Just create Bedrock agents
    python infra/setup.py --step api         # Just create API Gateway
    python infra/setup.py --dry-run          # Print plan without executing
"""

import os
import sys
import json
import time
import zipfile
import shutil
import argparse
import logging
import subprocess
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infra.config import (
    ACCOUNT_ID, REGION, MODEL_ID, S3_BUCKET,
    LAMBDA_ZIPS_PREFIX,
    RDS_HOST, RDS_PORT, RDS_DB, RDS_USER, RDS_PASSWORD,
    BEDROCK_AGENT_ROLE_ARN, LAMBDA_EXECUTION_ROLE_ARN, API_GATEWAY_ROLE_ARN,
    LAMBDA_RUNTIME, LAMBDA_TIMEOUT, LAMBDA_MEMORY, LAMBDA_FUNCTIONS, LAMBDA_ENV_VARS,
    AGENTS,
    SUPERVISOR_INSTRUCTIONS, VISIT_CAPTURE_INSTRUCTIONS,
    DEALER_INTELLIGENCE_INSTRUCTIONS, ORDER_PLANNING_INSTRUCTIONS,
    DEALER_ACTION_FUNCTIONS, VISIT_ACTION_FUNCTIONS,
    ORDER_ACTION_FUNCTIONS, ANALYTICS_ACTION_FUNCTIONS,
    API_GATEWAY_NAME, API_STAGE, RESOURCE_TAGS,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ─── State file to persist created resource IDs ───────────────────────────────
STATE_FILE = PROJECT_ROOT / "infra" / "state.json"


def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2, default=str))
    logger.info(f"State saved to {STATE_FILE}")


# ─── AWS Clients ──────────────────────────────────────────────────────────────
def get_clients():
    session = boto3.session.Session(region_name=REGION)
    return {
        "s3": session.client("s3"),
        "lambda": session.client("lambda"),
        "bedrock": session.client("bedrock-agent"),
        "logs": session.client("logs"),
        "apigateway": session.client("apigateway"),
        "iam": session.client("iam"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: (Deprecated) DB is now on RDS PostgreSQL — no upload needed
# ─────────────────────────────────────────────────────────────────────────────

def upload_db(clients, dry_run=False):
    """DEPRECATED — DB is now on RDS PostgreSQL. Use scripts/migrate_sqlite_to_pg.py."""
    logger.info("=" * 60)
    logger.info("STEP 1: DB is on RDS PostgreSQL — skipping SQLite S3 upload")
    logger.info(f"  RDS endpoint: {RDS_HOST}")
    logger.info(f"  Database    : {RDS_DB}")
    logger.info("  To migrate data: python scripts/migrate_sqlite_to_pg.py")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Create CloudWatch Log Groups
# ─────────────────────────────────────────────────────────────────────────────

def create_log_groups(clients, dry_run=False):
    """Create CloudWatch log groups for each Lambda."""
    logger.info("=" * 60)
    logger.info("STEP 2: Creating CloudWatch Log Groups")
    logs_client = clients["logs"]

    for key, cfg in LAMBDA_FUNCTIONS.items():
        log_group = cfg["log_group"]
        logger.info(f"  {log_group}")
        if dry_run:
            continue
        try:
            logs_client.create_log_group(logGroupName=log_group)
            logs_client.put_retention_policy(logGroupName=log_group, retentionInDays=7)
            logger.info(f"    ✅ Created")
        except logs_client.exceptions.ResourceAlreadyExistsException:
            logger.info(f"    ℹ️  Already exists")
        except ClientError as e:
            logger.warning(f"    ⚠️  {e}")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Package and Deploy Lambda Functions
# ─────────────────────────────────────────────────────────────────────────────

def package_lambda(lambda_key: str, cfg: dict) -> Path:
    """
    Package Lambda function + shared utilities + dependencies into a zip.
    """
    source_dir = PROJECT_ROOT / cfg["source_dir"]
    shared_dir = PROJECT_ROOT / "lambdas" / "shared"

    build_dir = Path(tempfile.mkdtemp()) / f"build_{lambda_key}"
    build_dir.mkdir(parents=True, exist_ok=True)

    # Copy handler
    shutil.copy(source_dir / "handler.py", build_dir / "handler.py")

    # Copy shared utilities as 'shared' package
    shared_build = build_dir / "shared"
    shared_build.mkdir()
    for f in shared_dir.glob("*.py"):
        shutil.copy(f, shared_build / f.name)

    # Install dependencies if requirements.txt exists
    req_file = source_dir / "requirements.txt"
    if not req_file.exists():
        # Use shared requirements
        req_file = PROJECT_ROOT / "lambdas" / "requirements.txt"

    if req_file.exists():
        logger.info(f"    Installing dependencies from {req_file} for Amazon Linux (Python 3.11)")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(req_file),
             "-t", str(build_dir), "--quiet",
             "--platform", "manylinux2014_x86_64",
             "--python-version", "3.11",
             "--only-binary=:all:"],
            check=True,
        )

    # Create zip
    zip_path = Path(tempfile.mkdtemp()) / f"{lambda_key}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in build_dir.rglob("*"):
            if item.is_file():
                # Skip __pycache__ and .pyc files
                if "__pycache__" in str(item) or item.suffix == ".pyc":
                    continue
                arcname = item.relative_to(build_dir)
                zf.write(item, arcname)

    size_kb = zip_path.stat().st_size / 1024
    logger.info(f"    Packaged: {zip_path.name} ({size_kb:.0f} KB)")
    return zip_path


def deploy_lambda(clients, lambda_key: str, cfg: dict, state: dict, dry_run=False) -> str:
    """Deploy a single Lambda function. Returns function ARN."""
    fn_name = cfg["name"]
    logger.info(f"  {fn_name}")

    if dry_run:
        logger.info(f"    [DRY RUN] Would package and deploy {fn_name}")
        return f"arn:aws:lambda:{REGION}:{ACCOUNT_ID}:function:{fn_name}"

    # Package
    zip_path = package_lambda(lambda_key, cfg)

    # Upload zip to S3
    s3_zip_key = f"{LAMBDA_ZIPS_PREFIX}{lambda_key}.zip"
    clients["s3"].upload_file(str(zip_path), S3_BUCKET, s3_zip_key)

    # Create or update function
    lc = clients["lambda"]
    existing_arn = state.get("lambdas", {}).get(lambda_key, {}).get("arn")

    try:
        if existing_arn:
            # Update existing function code
            response = lc.update_function_code(
                FunctionName=fn_name,
                S3Bucket=S3_BUCKET,
                S3Key=s3_zip_key,
            )
            time.sleep(2)  # Wait for update to propagate
            # Update configuration
            lc.update_function_configuration(
                FunctionName=fn_name,
                Runtime=LAMBDA_RUNTIME,
                Handler=cfg["handler"],
                Timeout=LAMBDA_TIMEOUT,
                MemorySize=LAMBDA_MEMORY,
                Environment={"Variables": LAMBDA_ENV_VARS},
            )
            fn_arn = response["FunctionArn"]
            logger.info(f"    ✅ Updated: {fn_arn}")
        else:
            # Create new function
            response = lc.create_function(
                FunctionName=fn_name,
                Runtime=LAMBDA_RUNTIME,
                Role=LAMBDA_EXECUTION_ROLE_ARN,
                Handler=cfg["handler"],
                Code={"S3Bucket": S3_BUCKET, "S3Key": s3_zip_key},
                Description=cfg["description"],
                Timeout=LAMBDA_TIMEOUT,
                MemorySize=LAMBDA_MEMORY,
                Environment={"Variables": LAMBDA_ENV_VARS},
                Tags=RESOURCE_TAGS,
            )
            fn_arn = response["FunctionArn"]
            logger.info(f"    ✅ Created: {fn_arn}")
            time.sleep(3)  # Wait for function to become active

    except ClientError as e:
        if "ResourceConflictException" in str(e) or "already exist" in str(e).lower():
            # Function exists but we don't have it in state, update it
            response = lc.get_function(FunctionName=fn_name)
            fn_arn = response["Configuration"]["FunctionArn"]
            lc.update_function_code(FunctionName=fn_name, S3Bucket=S3_BUCKET, S3Key=s3_zip_key)
            logger.info(f"    ✅ Code updated (existed): {fn_arn}")
        else:
            logger.error(f"    ❌ Failed: {e}")
            raise

    # Add Bedrock resource-based policy to allow agent invocation
    try:
        lc.add_permission(
            FunctionName=fn_name,
            StatementId="AllowBedrockAgent",
            Action="lambda:InvokeFunction",
            Principal="bedrock.amazonaws.com",
            SourceAccount=ACCOUNT_ID,
        )
    except ClientError as e:
        if "already exists" in str(e).lower():
            pass  # already added
        else:
            logger.warning(f"    ⚠️  Could not add Bedrock permission: {e}")

    return fn_arn


def deploy_lambdas(clients, state, dry_run=False):
    """Deploy all Lambda functions."""
    logger.info("=" * 60)
    logger.info("STEP 3: Packaging and Deploying Lambda Functions")

    if "lambdas" not in state:
        state["lambdas"] = {}

    for key, cfg in LAMBDA_FUNCTIONS.items():
        try:
            arn = deploy_lambda(clients, key, cfg, state, dry_run)
            if not dry_run:
                state["lambdas"][key] = {"arn": arn, "name": cfg["name"]}
                save_state(state)
        except Exception as e:
            logger.error(f"  ❌ Failed to deploy {key}: {e}")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Create Bedrock Agents
# ─────────────────────────────────────────────────────────────────────────────

def _build_function_schema(functions: list) -> dict:
    """Build functionSchema dict for create_agent_action_group."""
    functions_list = []
    for f in functions:
        params = {}
        for pname, pinfo in f["parameters"].items():
            params[pname] = {
                "description": pinfo["description"],
                "type": pinfo["type"],
                "required": pinfo["required"],
            }
        functions_list.append({
            "name": f["name"],
            "description": f["description"],
            "parameters": params,
        })
    return {"functions": functions_list}


def wait_for_agent_ready(bedrock_client, agent_id: str, timeout: int = 120):
    """Poll until agent reaches NOT_PREPARED or PREPARED state."""
    start = time.time()
    while time.time() - start < timeout:
        resp = bedrock_client.get_agent(agentId=agent_id)
        status = resp["agent"]["agentStatus"]
        if status in ("NOT_PREPARED", "PREPARED", "FAILED"):
            return status
        logger.info(f"    Agent status: {status}, waiting...")
        time.sleep(5)
    return "TIMEOUT"


def create_bedrock_agent(bedrock, agent_key: str, cfg: dict, instructions: str,
                          state: dict, dry_run=False) -> dict:
    """Create a Bedrock agent and return {agent_id, agent_arn}."""
    agent_name = cfg["name"]
    logger.info(f"  {agent_name}")

    if dry_run:
        logger.info(f"    [DRY RUN] Would create agent: {agent_name}")
        return {"agent_id": f"mock-{agent_key}", "agent_arn": f"arn:mock:{agent_key}"}

    existing = state.get("agents", {}).get(agent_key, {})
    if existing.get("agent_id"):
        agent_id = existing["agent_id"]
        logger.info(f"    ℹ️  Already exists: {agent_id}")
        # Update instructions
        try:
            bedrock.update_agent(
                agentId=agent_id,
                agentName=agent_name,
                agentResourceRoleArn=BEDROCK_AGENT_ROLE_ARN,
                foundationModel=MODEL_ID,
                instruction=instructions,
                description=cfg["description"],
                idleSessionTTLInSeconds=1800,
                agentCollaboration=cfg["collaboration"],
            )
            logger.info(f"    ✅ Instructions updated")
        except ClientError as e:
            logger.warning(f"    ⚠️  Could not update: {e}")
        return existing

    response = bedrock.create_agent(
        agentName=agent_name,
        agentResourceRoleArn=BEDROCK_AGENT_ROLE_ARN,
        foundationModel=MODEL_ID,
        instruction=instructions,
        description=cfg["description"],
        idleSessionTTLInSeconds=1800,
        agentCollaboration=cfg["collaboration"],
        tags=RESOURCE_TAGS,
    )
    agent = response["agent"]
    agent_id = agent["agentId"]
    agent_arn = agent["agentArn"]

    logger.info(f"    ✅ Created: {agent_id}")

    # Wait for agent to reach NOT_PREPARED
    status = wait_for_agent_ready(bedrock, agent_id)
    logger.info(f"    Status: {status}")

    return {"agent_id": agent_id, "agent_arn": agent_arn}


def create_action_group(bedrock, agent_id: str, ag_name: str, lambda_arn: str,
                         functions: list, dry_run=False) -> str:
    """Create action group for an agent."""
    logger.info(f"    Action group: {ag_name}")

    if dry_run:
        return f"mock-ag-{ag_name}"

    function_schema = _build_function_schema(functions)

    try:
        response = bedrock.create_agent_action_group(
            agentId=agent_id,
            agentVersion="DRAFT",
            actionGroupName=ag_name,
            description=f"Action group for {ag_name}",
            actionGroupExecutor={"lambda": lambda_arn},
            functionSchema=function_schema,
        )
        ag_id = response["agentActionGroup"]["actionGroupId"]
        logger.info(f"      ✅ {ag_id}")
        return ag_id
    except ClientError as e:
        if "already exists" in str(e).lower() or "ConflictException" in str(e):
            logger.info(f"      ℹ️  Already exists")
            return "exists"
        logger.error(f"      ❌ {e}")
        raise


def prepare_agent(bedrock, agent_id: str, dry_run=False):
    """Prepare (compile) the agent."""
    if dry_run:
        return
    logger.info(f"    Preparing agent {agent_id}...")
    bedrock.prepare_agent(agentId=agent_id)
    time.sleep(10)  # Give it time to prepare
    status = wait_for_agent_ready(bedrock, agent_id, timeout=180)
    logger.info(f"    Prepared, status: {status}")


def create_agent_alias(bedrock, agent_id: str, alias_name: str, dry_run=False) -> str:
    """Create an agent alias pointing to DRAFT version."""
    if dry_run:
        return f"mock-alias-{alias_name}"

    logger.info(f"    Creating alias '{alias_name}'...")
    try:
        response = bedrock.create_agent_alias(
            agentId=agent_id,
            agentAliasName=alias_name,
            description=f"Production alias for {alias_name}",
            tags=RESOURCE_TAGS,
        )
        alias_id = response["agentAlias"]["agentAliasId"]
        logger.info(f"    ✅ Alias: {alias_id}")
        time.sleep(5)
        return alias_id
    except ClientError as e:
        if "already exists" in str(e).lower():
            # Get existing alias
            aliases = bedrock.list_agent_aliases(agentId=agent_id)["agentAliasSummaries"]
            for a in aliases:
                if a["agentAliasName"] == alias_name:
                    logger.info(f"    ℹ️  Using existing alias: {a['agentAliasId']}")
                    return a["agentAliasId"]
        logger.error(f"    ❌ {e}")
        raise


def deploy_agents(clients, state, dry_run=False):
    """Create all Bedrock agents with action groups."""
    logger.info("=" * 60)
    logger.info("STEP 4: Creating Bedrock Agents")
    bedrock = clients["bedrock"]

    if "agents" not in state:
        state["agents"] = {}

    lambdas = state.get("lambdas", {})

    # Map: agent_key → (instructions, action_group_name, lambda_key, functions)
    agent_configs = {
        "dealer_intelligence": (
            DEALER_INTELLIGENCE_INSTRUCTIONS,
            "DealerActionGroup",
            "dealer_actions",
            DEALER_ACTION_FUNCTIONS,
        ),
        "visit_capture": (
            VISIT_CAPTURE_INSTRUCTIONS,
            "VisitActionGroup",
            "visit_actions",
            VISIT_ACTION_FUNCTIONS,
        ),
        "order_planning": (
            ORDER_PLANNING_INSTRUCTIONS,
            "OrderActionGroup",
            "order_actions",
            ORDER_ACTION_FUNCTIONS,
        ),
    }

    # Step 4a: Create the 3 collaborator agents first
    logger.info("\n--- 4a: Creating Collaborator Agents ---")
    for agent_key, (instructions, ag_name, lambda_key, functions) in agent_configs.items():
        cfg = AGENTS[agent_key]
        agent_info = create_bedrock_agent(bedrock, agent_key, cfg, instructions, state, dry_run)
        state["agents"][agent_key] = agent_info
        if not dry_run:
            save_state(state)

        if not dry_run and agent_info.get("agent_id"):
            agent_id = agent_info["agent_id"]
            lambda_arn = lambdas.get(lambda_key, {}).get("arn", "")
            if not lambda_arn and not dry_run:
                logger.warning(f"    ⚠️  Lambda ARN not found for {lambda_key} — deploy lambdas first!")
                continue

            # Create action group
            if lambda_arn:
                ag_id = create_action_group(bedrock, agent_id, ag_name, lambda_arn, functions, dry_run)
                state["agents"][agent_key]["action_group_id"] = ag_id

            # Prepare agent
            prepare_agent(bedrock, agent_id, dry_run)

            # Create alias
            alias_id = create_agent_alias(bedrock, agent_id, "prod", dry_run)
            state["agents"][agent_key]["alias_id"] = alias_id

            # Build alias ARN for later use with supervisor
            alias_arn = f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{agent_id}/{alias_id}"
            state["agents"][agent_key]["alias_arn"] = alias_arn

            save_state(state)

    # Step 4b: Create Supervisor Agent
    logger.info("\n--- 4b: Creating Supervisor Agent ---")
    sup_cfg = AGENTS["supervisor"]
    sup_info = create_bedrock_agent(
        bedrock, "supervisor", sup_cfg, SUPERVISOR_INSTRUCTIONS, state, dry_run
    )
    state["agents"]["supervisor"] = sup_info
    if not dry_run:
        save_state(state)

    if not dry_run and sup_info.get("agent_id"):
        sup_id = sup_info["agent_id"]

        # Step 4c: Associate collaborators with supervisor
        logger.info("\n--- 4c: Associating Collaborators with Supervisor ---")
        for agent_key, cfg_tuple in agent_configs.items():
            agent_data = state["agents"].get(agent_key, {})
            alias_arn = agent_data.get("alias_arn", "")
            if not alias_arn:
                logger.warning(f"    ⚠️  No alias ARN for {agent_key}, skipping association")
                continue

            collab_name = {
                "dealer_intelligence": "Dealer_Intelligence_Agent",
                "visit_capture": "Visit_Capture_Agent",
                "order_planning": "Order_Planning_Agent",
            }[agent_key]

            collab_instruction = {
                "dealer_intelligence": (
                    "Route to Dealer_Intelligence_Agent for: dealer briefings, payment status, "
                    "health scores, visit planning, rep dashboard metrics"
                ),
                "visit_capture": (
                    "Route to Visit_Capture_Agent when user is logging a dealer visit, "
                    "describing what happened during a visit, recording commitments or payments"
                ),
                "order_planning": (
                    "Route to Order_Planning_Agent for: order creation, inventory checks, "
                    "commitment fulfillment tracking, forecast consumption"
                ),
            }[agent_key]

            logger.info(f"    Associating {collab_name}...")
            try:
                bedrock.associate_agent_collaborator(
                    agentId=sup_id,
                    agentVersion="DRAFT",
                    agentDescriptor={"aliasArn": alias_arn},
                    collaboratorName=collab_name,
                    collaborationInstruction=collab_instruction,
                    relayConversationHistory="TO_COLLABORATOR",
                )
                logger.info(f"    ✅ Associated {collab_name}")
            except ClientError as e:
                if "already exists" in str(e).lower() or "ConflictException" in str(e):
                    logger.info(f"    ℹ️  Already associated")
                else:
                    logger.error(f"    ❌ {e}")

        # Prepare supervisor
        prepare_agent(bedrock, sup_id, dry_run)

        # Create supervisor alias
        sup_alias_id = create_agent_alias(bedrock, sup_id, "prod", dry_run)
        sup_alias_arn = f"arn:aws:bedrock:{REGION}:{ACCOUNT_ID}:agent-alias/{sup_id}/{sup_alias_id}"
        state["agents"]["supervisor"]["alias_id"] = sup_alias_id
        state["agents"]["supervisor"]["alias_arn"] = sup_alias_arn
        save_state(state)

        logger.info(f"\n  ✅ SUPERVISOR AGENT READY")
        logger.info(f"     Agent ID:  {sup_id}")
        logger.info(f"     Alias ID:  {sup_alias_id}")
        logger.info(f"     Alias ARN: {sup_alias_arn}")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Create API Gateway
# ─────────────────────────────────────────────────────────────────────────────

def create_api_gateway(clients, state, dry_run=False):
    """Create REST API Gateway for dashboard + webhook."""
    logger.info("=" * 60)
    logger.info("STEP 5: Creating API Gateway")
    apigw = clients["apigateway"]

    if dry_run:
        logger.info("  [DRY RUN] Would create API Gateway")
        return True

    # Create API or reuse existing
    existing_api_id = state.get("api_gateway", {}).get("api_id")
    if existing_api_id:
        logger.info(f"  ℹ️  Using existing API: {existing_api_id}")
        api_id = existing_api_id
    else:
        response = apigw.create_rest_api(
            name=API_GATEWAY_NAME,
            description="SupplyChain Copilot API for Telegram webhook and React dashboard",
            endpointConfiguration={"types": ["REGIONAL"]},
            tags=RESOURCE_TAGS,
        )
        api_id = response["id"]
        logger.info(f"  ✅ API created: {api_id}")

    state.setdefault("api_gateway", {})["api_id"] = api_id

    # Get root resource
    resources = apigw.get_resources(restApiId=api_id)["items"]
    root_id = next(r["id"] for r in resources if r["path"] == "/")

    lambdas = state.get("lambdas", {})

    # Helper to create resource + POST/GET method + Lambda integration
    def ensure_resource(path_part, parent_id):
        for r in apigw.get_resources(restApiId=api_id)["items"]:
            if r.get("pathPart") == path_part and r.get("parentId") == parent_id:
                return r["id"]
        resp = apigw.create_resource(restApiId=api_id, parentId=parent_id, pathPart=path_part)
        return resp["id"]

    def grant_apigw_invoke(fn_name):
        """Allow API Gateway to invoke a Lambda function."""
        lc = clients["lambda"]
        stmt_id = f"AllowAPIGateway-{api_id}"
        try:
            lc.add_permission(
                FunctionName=fn_name,
                StatementId=stmt_id,
                Action="lambda:InvokeFunction",
                Principal="apigateway.amazonaws.com",
                SourceArn=f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/*/*",
            )
            logger.info(f"    ✅ API Gateway invoke permission granted to {fn_name}")
        except ClientError as e:
            if "already exists" in str(e).lower():
                logger.info(f"    ℹ️  Permission already exists for {fn_name}")
            else:
                logger.warning(f"    ⚠️  Could not grant permission to {fn_name}: {e}")

    def add_method(resource_id, http_method, lambda_fn_name):
        lambda_arn = lambdas.get(lambda_fn_name, {}).get("arn", "")
        if not lambda_arn:
            logger.warning(f"    ⚠️  No Lambda ARN for {lambda_fn_name}")
            return

        # Create method (skip if already exists)
        try:
            apigw.put_method(
                restApiId=api_id,
                resourceId=resource_id,
                httpMethod=http_method,
                authorizationType="NONE",
            )
        except ClientError as e:
            if "ConflictException" not in str(e):
                raise

        # Force-update integration (delete existing first so we can change the target Lambda)
        uri = f"arn:aws:apigateway:{REGION}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"
        try:
            apigw.delete_integration(restApiId=api_id, resourceId=resource_id, httpMethod=http_method)
        except ClientError:
            pass  # Did not exist yet — that's fine

        apigw.put_integration(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            type="AWS_PROXY",
            integrationHttpMethod="POST",
            uri=uri,
        )

        # Add OPTIONS for CORS (skip if already set up)
        try:
            apigw.put_method(restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS", authorizationType="NONE")
            apigw.put_method_response(restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS", statusCode="200",
                                       responseParameters={"method.response.header.Access-Control-Allow-Headers": False,
                                                           "method.response.header.Access-Control-Allow-Methods": False,
                                                           "method.response.header.Access-Control-Allow-Origin": False})
            apigw.put_integration(restApiId=api_id, resourceId=resource_id, httpMethod="OPTIONS", type="MOCK",
                                   requestTemplates={"application/json": '{"statusCode": 200}'})
        except ClientError:
            pass  # Already set up

    # Grant API Gateway invoke permission for each Lambda used by the API
    for fn_key in ["telegram_webhook", "dashboard_api", "analytics_actions"]:
        fn_name = lambdas.get(fn_key, {}).get("name", "")
        if fn_name:
            grant_apigw_invoke(fn_name)

    # /webhook → telegram_webhook (POST)
    webhook_id = ensure_resource("webhook", root_id)
    add_method(webhook_id, "POST", "telegram_webhook")
    logger.info("  ✅ /webhook → telegram_webhook")

    # /chat → telegram_webhook (POST, for direct agent testing)
    chat_id = ensure_resource("chat", root_id)
    add_method(chat_id, "POST", "telegram_webhook")
    logger.info("  ✅ /chat → telegram_webhook")

    # /api resource (parent)
    api_resource_id = ensure_resource("api", root_id)

    # Dashboard endpoints → scm-dashboard-api Lambda
    dashboard_routes = [
        "metrics", "dealers", "revenue-chart", "commitment-pipeline",
        "sales-team", "recent-activity", "weekly-pipeline",
    ]
    for subpath in dashboard_routes:
        sub_id = ensure_resource(subpath, api_resource_id)
        add_method(sub_id, "GET", "dashboard_api")
        logger.info(f"  ✅ /api/{subpath} → dashboard_api")

    # /api/chat → telegram_webhook (POST) for the dashboard chat tab
    chat_api_id = ensure_resource("chat", api_resource_id)
    add_method(chat_api_id, "POST", "telegram_webhook")
    logger.info("  ✅ /api/chat → telegram_webhook")

    # Analytics endpoints → scm-analytics-actions Lambda (Bedrock agent / direct testing)
    analytics_routes = ["commitments", "alerts", "map"]
    for subpath in analytics_routes:
        sub_id = ensure_resource(subpath, api_resource_id)
        add_method(sub_id, "GET", "analytics_actions")
        logger.info(f"  ✅ /api/{subpath} → analytics_actions")

    # Deploy to prod stage
    try:
        deploy_response = apigw.create_deployment(
            restApiId=api_id,
            stageName=API_STAGE,
            description="Initial deployment",
        )
        stage_arn = f"arn:aws:execute-api:{REGION}:{ACCOUNT_ID}:{api_id}/{API_STAGE}/*"
        api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com/{API_STAGE}"

        state["api_gateway"]["url"] = api_url
        state["api_gateway"]["stage"] = API_STAGE
        save_state(state)

        logger.info(f"\n  ✅ API DEPLOYED")
        logger.info(f"     URL: {api_url}")
    except ClientError as e:
        logger.error(f"  ❌ Deployment failed: {e}")

    return True


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def print_summary(state):
    """Print final infrastructure summary."""
    print("\n" + "=" * 70)
    print("INFRASTRUCTURE SUMMARY")
    print("=" * 70)

    # Lambdas
    print("\n[LAMBDA FUNCTIONS]")
    for key, info in state.get("lambdas", {}).items():
        print(f"   {info.get('name', key)}: {info.get('arn', 'N/A')}")

    # Agents
    print("\n[BEDROCK AGENTS]")
    for key, info in state.get("agents", {}).items():
        print(f"   {key}:")
        print(f"      Agent ID: {info.get('agent_id', 'N/A')}")
        print(f"      Alias ID: {info.get('alias_id', 'N/A')}")

    # API Gateway
    api = state.get("api_gateway", {})
    if api:
        print("\n[API GATEWAY]")
        print(f"   URL: {api.get('url', 'N/A')}")

    # Test command
    sup = state.get("agents", {}).get("supervisor", {})
    if sup.get("agent_id") and sup.get("alias_id"):
        print("\n[READY] - Test the agent:")
        print("   python infra/test_agent.py")
        print(f"   Agent ID: {sup['agent_id']}")
        print(f"   Alias ID: {sup['alias_id']}")

    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="SupplyChain Copilot Infrastructure Setup")
    parser.add_argument("--step", choices=["upload_db", "log_groups", "lambdas", "agents", "api", "all"],
                        default="all", help="Which step to run")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    if args.dry_run:
        logger.info("🔍 DRY RUN MODE — No changes will be made")

    clients = get_clients()
    state = load_state()

    if args.step in ("all", "upload_db"):
        upload_db(clients, args.dry_run)

    if args.step in ("all", "log_groups"):
        create_log_groups(clients, args.dry_run)

    if args.step in ("all", "lambdas"):
        deploy_lambdas(clients, state, args.dry_run)

    if args.step in ("all", "agents"):
        deploy_agents(clients, state, args.dry_run)

    if args.step in ("all", "api"):
        create_api_gateway(clients, state, args.dry_run)

    if args.step == "all":
        print_summary(state)

    logger.info("✅ Done!")


if __name__ == "__main__":
    main()
