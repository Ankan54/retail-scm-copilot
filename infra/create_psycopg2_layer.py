#!/usr/bin/env python3
"""
Create a Lambda Layer with psycopg2-binary for Python 3.11 on Amazon Linux 2023.
This layer can be attached to all Lambda functions that need PostgreSQL connectivity.

Usage:
    python infra/create_psycopg2_layer.py
"""

import os
import sys
import json
import shutil
import zipfile
import tempfile
import subprocess
import logging
from pathlib import Path

import boto3
from botocore.exceptions import ClientError

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from infra.config import ACCOUNT_ID, REGION, S3_BUCKET, RESOURCE_TAGS

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

LAYER_NAME = "psycopg2-layer"
PYTHON_VERSION = "3.11"


def create_layer_package():
    """Build Lambda Layer zip with psycopg2-binary."""
    logger.info("Building Lambda Layer package...")
    
    # Create temp directory structure: python/lib/python3.11/site-packages/
    build_dir = Path(tempfile.mkdtemp()) / "layer"
    python_dir = build_dir / "python"
    python_dir.mkdir(parents=True)
    
    logger.info(f"  Build directory: {build_dir}")
    
    # Install psycopg2-binary using Docker to match Lambda environment
    # This ensures compatibility with Amazon Linux 2023
    logger.info("  Installing psycopg2-binary for Amazon Linux 2023...")
    
    try:
        # Try using Docker first (most reliable)
        subprocess.run([
            "docker", "run", "--rm",
            "-v", f"{python_dir}:/var/task",
            "public.ecr.aws/lambda/python:3.11",
            "pip", "install",
            "psycopg2-binary==2.9.9",
            "-t", "/var/task",
            "--no-cache-dir"
        ], check=True)
        logger.info("  ✅ Installed using Docker")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.warning("  Docker not available, trying pip with platform flag...")
        # Fallback to pip with platform specification
        subprocess.run([
            sys.executable, "-m", "pip", "install",
            "psycopg2-binary==2.9.9",
            "-t", str(python_dir),
            "--platform", "manylinux2014_x86_64",
            "--python-version", PYTHON_VERSION,
            "--only-binary=:all:",
            "--no-cache-dir"
        ], check=True)
        logger.info("  ✅ Installed using pip")
    
    # Create zip file
    zip_path = Path(tempfile.mkdtemp()) / f"{LAYER_NAME}.zip"
    logger.info(f"  Creating zip: {zip_path}")
    
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in build_dir.rglob("*"):
            if item.is_file():
                # Skip unnecessary files
                if "__pycache__" in str(item) or item.suffix in (".pyc", ".dist-info"):
                    continue
                arcname = item.relative_to(build_dir)
                zf.write(item, arcname)
    
    size_mb = zip_path.stat().st_size / 1024 / 1024
    logger.info(f"  ✅ Package created: {size_mb:.1f} MB")
    
    return zip_path


def upload_and_publish_layer(zip_path: Path):
    """Upload layer zip to S3 and publish as Lambda Layer."""
    logger.info("Publishing Lambda Layer...")
    
    session = boto3.session.Session(region_name=REGION)
    s3_client = session.client("s3")
    lambda_client = session.client("lambda")
    
    # Upload to S3
    s3_key = f"lambda-layers/{LAYER_NAME}.zip"
    logger.info(f"  Uploading to s3://{S3_BUCKET}/{s3_key}")
    s3_client.upload_file(str(zip_path), S3_BUCKET, s3_key)
    logger.info("  ✅ Uploaded to S3")
    
    # Publish layer version
    try:
        response = lambda_client.publish_layer_version(
            LayerName=LAYER_NAME,
            Description="psycopg2-binary 2.9.9 for PostgreSQL connectivity",
            Content={
                "S3Bucket": S3_BUCKET,
                "S3Key": s3_key,
            },
            CompatibleRuntimes=["python3.11"],
            CompatibleArchitectures=["x86_64"],
        )
        
        layer_arn = response["LayerVersionArn"]
        version = response["Version"]
        
        logger.info(f"  ✅ Layer published: {layer_arn}")
        logger.info(f"     Version: {version}")
        
        return layer_arn, version
        
    except ClientError as e:
        logger.error(f"  ❌ Failed to publish layer: {e}")
        raise


def attach_layer_to_functions(layer_arn: str):
    """Attach the layer to all Lambda functions."""
    logger.info("Attaching layer to Lambda functions...")
    
    from infra.config import LAMBDA_FUNCTIONS
    
    session = boto3.session.Session(region_name=REGION)
    lambda_client = session.client("lambda")
    
    for key, cfg in LAMBDA_FUNCTIONS.items():
        fn_name = cfg["name"]
        logger.info(f"  {fn_name}")
        
        try:
            # Get current function config
            response = lambda_client.get_function_configuration(FunctionName=fn_name)
            current_layers = response.get("Layers", [])
            current_layer_arns = [layer["Arn"] for layer in current_layers]
            
            # Remove old versions of our layer
            layer_base = layer_arn.rsplit(":", 1)[0]  # Remove version number
            filtered_layers = [arn for arn in current_layer_arns if not arn.startswith(layer_base)]
            
            # Add new layer version
            new_layers = filtered_layers + [layer_arn]
            
            # Update function
            lambda_client.update_function_configuration(
                FunctionName=fn_name,
                Layers=new_layers
            )
            logger.info(f"    ✅ Layer attached")
            
        except ClientError as e:
            if "ResourceNotFoundException" in str(e):
                logger.warning(f"    ⚠️  Function not found (deploy it first)")
            else:
                logger.error(f"    ❌ Failed: {e}")


def main():
    logger.info("=" * 70)
    logger.info("Creating psycopg2 Lambda Layer")
    logger.info("=" * 70)
    
    # Step 1: Build layer package
    zip_path = create_layer_package()
    
    # Step 2: Upload and publish
    layer_arn, version = upload_and_publish_layer(zip_path)
    
    # Step 3: Attach to functions
    attach_layer_to_functions(layer_arn)
    
    logger.info("\n" + "=" * 70)
    logger.info("✅ LAYER CREATED AND ATTACHED")
    logger.info("=" * 70)
    logger.info(f"Layer ARN: {layer_arn}")
    logger.info(f"Version: {version}")
    logger.info("\nYou can now test your Lambda functions in the AWS console!")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
