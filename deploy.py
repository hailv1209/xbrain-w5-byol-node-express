#!/usr/bin/env python3
"""
AWS Lambda deployment script for byol-node-express
Handles: IAM role, Lambda function, HTTP API Gateway, permissions
"""

import json
import boto3
import time
import sys
from pathlib import Path

# Configuration
FUNCTION_NAME = "byol-node-express"
REGION = "us-west-2"
ROLE_NAME = "byol-node-express-role"
ZIP_FILE = "function.zip"
RUNTIME = "nodejs22.x"
HANDLER = "lambda.handler"
ARCHITECTURE = "arm64"
TIMEOUT = 10
MEMORY_SIZE = 512

# Initialize clients
iam = boto3.client("iam")
lambda_client = boto3.client("lambda", region_name=REGION)
apigateway = boto3.client("apigatewayv2", region_name=REGION)
sts = boto3.client("sts", region_name=REGION)

def log(msg, level="INFO"):
    """Simple logging"""
    levels = {"INFO": "🔵", "OK": "✓", "WARN": "⚠️", "ERROR": "❌"}
    icon = levels.get(level, "•")
    print(f"{icon} {msg}")

def create_iam_role():
    """Create or get IAM role for Lambda"""
    log("Creating/checking IAM role...", "INFO")
    
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    try:
        role = iam.get_role(RoleName=ROLE_NAME)
        role_arn = role["Role"]["Arn"]
        log(f"Role exists: {role_arn}", "OK")
        return role_arn
    except iam.exceptions.NoSuchEntityException:
        log(f"Creating new role: {ROLE_NAME}")
        
        role = iam.create_role(
            RoleName=ROLE_NAME,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        role_arn = role["Role"]["Arn"]
        
        # Attach execution policy
        iam.attach_role_policy(
            RoleName=ROLE_NAME,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        
        time.sleep(3)  # Wait for role to be available
        log(f"Role created: {role_arn}", "OK")
        return role_arn

def create_or_update_lambda(role_arn):
    """Create or update Lambda function"""
    log("Setting up Lambda function...", "INFO")
    
    if not Path(ZIP_FILE).exists():
        log(f"{ZIP_FILE} not found!", "ERROR")
        sys.exit(1)
    
    with open(ZIP_FILE, "rb") as f:
        zip_content = f.read()
    
    try:
        # Update existing function
        lambda_client.get_function(FunctionName=FUNCTION_NAME)
        log(f"Function exists, updating code...", "WARN")
        
        lambda_client.update_function_code(
            FunctionName=FUNCTION_NAME,
            ZipFile=zip_content
        )
        
        lambda_client.update_function_configuration(
            FunctionName=FUNCTION_NAME,
            Handler=HANDLER,
            Timeout=TIMEOUT,
            MemorySize=MEMORY_SIZE,
            Architectures=[ARCHITECTURE],
            TracingConfig={"Mode": "Active"}
        )
        
        log("Lambda function updated", "OK")
    except lambda_client.exceptions.ResourceNotFoundException:
        # Create new function
        log(f"Creating new Lambda function: {FUNCTION_NAME}", "INFO")
        
        lambda_client.create_function(
            FunctionName=FUNCTION_NAME,
            Runtime=RUNTIME,
            Role=role_arn,
            Handler=HANDLER,
            Code={"ZipFile": zip_content},
            Architectures=[ARCHITECTURE],
            Timeout=TIMEOUT,
            MemorySize=MEMORY_SIZE,
            TracingConfig={"Mode": "Active"}
        )
        
        log("Lambda function created", "OK")
        time.sleep(2)

def get_lambda_arn():
    """Get Lambda function ARN"""
    response = lambda_client.get_function(FunctionName=FUNCTION_NAME)
    return response["Configuration"]["FunctionArn"]

def create_or_get_http_api():
    """Create or get HTTP API"""
    log("Setting up HTTP API Gateway...", "INFO")
    
    lambda_arn = get_lambda_arn()
    account_id = sts.get_caller_identity()["Account"]
    
    # Check if API exists
    apis = apigateway.get_apis()
    for api in apis.get("Items", []):
        if api.get("Name") == FUNCTION_NAME:
            log(f"API exists: {api['ApiId']}", "OK")
            return api["ApiId"]
    
    # Create new API
    log("Creating new HTTP API...", "INFO")
    api_response = apigateway.create_api(
        Name=FUNCTION_NAME,
        ProtocolType="HTTP",
        Target=lambda_arn
    )
    api_id = api_response["ApiId"]
    
    log(f"HTTP API created: {api_id}", "OK")
    return api_id

def add_lambda_permission():
    """Allow API Gateway to invoke Lambda"""
    log("Configuring Lambda permissions...", "INFO")
    
    try:
        lambda_client.get_policy(FunctionName=FUNCTION_NAME)
        log("Permissions already configured", "OK")
    except lambda_client.exceptions.ResourceNotFoundException:
        lambda_client.add_permission(
            FunctionName=FUNCTION_NAME,
            StatementId="AllowAPIGatewayInvoke",
            Action="lambda:InvokeFunction",
            Principal="apigateway.amazonaws.com"
        )
        log("Permission added for API Gateway", "OK")

def test_endpoints(api_url):
    """Test deployed endpoints"""
    log("Testing API endpoints...", "INFO")
    time.sleep(2)
    
    import urllib.request
    import json as json_lib
    
    endpoints = [
        (f"{api_url}/", "GET"),
        (f"{api_url}/api/hello/world", "GET"),
    ]
    
    for url, method in endpoints:
        try:
            req = urllib.request.Request(url, method=method)
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json_lib.loads(response.read())
                log(f"✓ {method} {url.replace(api_url, '')}: {response.status}", "OK")
                print(f"  Response: {json_lib.dumps(data, indent=2)[:100]}...")
        except Exception as e:
            log(f"✗ {method} {url}: {str(e)[:50]}", "WARN")

def main():
    """Main deployment flow"""
    print("\n" + "="*60)
    print("🚀 DEPLOYING BYOL NODE EXPRESS TO AWS LAMBDA")
    print("="*60 + "\n")
    
    try:
        # Step 1: IAM Role
        print("\n[STEP 1/5] IAM Role")
        role_arn = create_iam_role()
        
        # Step 2: Lambda Function
        print("\n[STEP 2/5] Lambda Function")
        create_or_update_lambda(role_arn)
        
        # Step 3: HTTP API
        print("\n[STEP 3/5] HTTP API Gateway")
        api_id = create_or_get_http_api()
        
        # Step 4: Permissions
        print("\n[STEP 4/5] Permissions")
        add_lambda_permission()
        
        # Step 5: Test
        print("\n[STEP 5/5] Testing")
        api_url = f"https://{api_id}.execute-api.{REGION}.amazonaws.com"
        test_endpoints(api_url)
        
        # Success output
        print("\n" + "="*60)
        print("✅ DEPLOYMENT SUCCESSFUL!")
        print("="*60)
        print(f"\n📍 API Gateway URL: {api_url}")
        print(f"📍 Lambda Function:  {FUNCTION_NAME}")
        print(f"📍 Region:           {REGION}")
        print("\n📝 Next steps:")
        print(f"   1. Test: curl {api_url}/")
        print(f"   2. Logs: aws logs tail /aws/lambda/{FUNCTION_NAME} --follow")
        print(f"   3. Invoke: aws lambda invoke --function-name {FUNCTION_NAME} response.json")
        print("\n" + "="*60 + "\n")
        
        return api_url
        
    except Exception as e:
        log(f"Deployment failed: {str(e)}", "ERROR")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
