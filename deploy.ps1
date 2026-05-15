# PowerShell deployment script for AWS Lambda

# Configuration
$functionName = "byol-node-express"
$region = "us-west-2"
$roleName = "byol-node-express-role"
$zipFile = "function.zip"
$runtime = "nodejs22.x"
$handler = "lambda.handler"
$architecture = "arm64"
$timeout = 10
$memorySize = 512

Write-Host "🚀 Deploying $functionName to AWS Lambda..." -ForegroundColor Cyan

# Step 1: Create IAM Role
Write-Host "`n[1/5] Creating IAM Role..." -ForegroundColor Yellow

$trustPolicyJson = @{
    Version = "2012-10-17"
    Statement = @(
        @{
            Effect = "Allow"
            Principal = @{
                Service = "lambda.amazonaws.com"
            }
            Action = "sts:AssumeRole"
        }
    )
} | ConvertTo-Json

# Check if role exists
$roleCheck = aws iam get-role --role-name $roleName --region $region 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Role $roleName already exists" -ForegroundColor Green
    $roleArn = ($roleCheck | ConvertFrom-Json).Role.Arn
} else {
    Write-Host "Creating new role..."
    $roleArn = (aws iam create-role `
        --role-name $roleName `
        --assume-role-policy-document $trustPolicyJson `
        --region $region 2>&1 | ConvertFrom-Json).Role.Arn
    
    # Attach basic Lambda execution policy
    aws iam attach-role-policy `
        --role-name $roleName `
        --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole" `
        --region $region
    
    # Wait for role to be available
    Start-Sleep -Seconds 3
}

Write-Host "✓ Role ARN: $roleArn" -ForegroundColor Green

# Step 2: Create or Update Lambda Function
Write-Host "`n[2/5] Creating/Updating Lambda Function..." -ForegroundColor Yellow

if (Test-Path $zipFile) {
    # Check if function exists
    $funcCheck = aws lambda get-function --function-name $functionName --region $region 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "Function exists, updating code..."
        aws lambda update-function-code `
            --function-name $functionName `
            --zip-file "fileb://$zipFile" `
            --region $region | Out-Null
        
        # Update configuration
        aws lambda update-function-configuration `
            --function-name $functionName `
            --handler $handler `
            --timeout $timeout `
            --memory-size $memorySize `
            --architectures $architecture `
            --region $region | Out-Null
        
        Write-Host "✓ Lambda function updated" -ForegroundColor Green
    } else {
        Write-Host "Creating new function..."
        aws lambda create-function `
            --function-name $functionName `
            --runtime $runtime `
            --role $roleArn `
            --handler $handler `
            --zip-file "fileb://$zipFile" `
            --architectures $architecture `
            --timeout $timeout `
            --memory-size $memorySize `
            --tracing-config Mode=Active `
            --region $region | Out-Null
        
        Write-Host "✓ Lambda function created" -ForegroundColor Green
        Start-Sleep -Seconds 2
    }
} else {
    Write-Host "❌ $zipFile not found!" -ForegroundColor Red
    exit 1
}

# Step 3: Create API Gateway (HTTP API)
Write-Host "`n[3/5] Setting up API Gateway..." -ForegroundColor Yellow

$apiCheck = aws apigatewayv2 get-apis --region $region 2>&1 | ConvertFrom-Json | 
    Select-Object -ExpandProperty Items | 
    Where-Object { $_.Name -eq $functionName }

if ($apiCheck) {
    $apiId = $apiCheck.ApiId
    Write-Host "✓ API Gateway already exists: $apiId" -ForegroundColor Green
} else {
    Write-Host "Creating new HTTP API..."
    $apiId = (aws apigatewayv2 create-api `
        --name $functionName `
        --protocol-type HTTP `
        --target "arn:aws:lambda:$region`:$((aws sts get-caller-identity 2>&1 | ConvertFrom-Json).Account):function:$functionName" `
        --region $region 2>&1 | ConvertFrom-Json).ApiId
    
    Write-Host "✓ API Gateway created: $apiId" -ForegroundColor Green
    Start-Sleep -Seconds 1
}

# Step 4: Add Lambda permission for API Gateway
Write-Host "`n[4/5] Configuring Lambda permissions..." -ForegroundColor Yellow

$permCheck = aws lambda get-policy --function-name $functionName --region $region 2>&1
if ($LASTEXITCODE -ne 0) {
    aws lambda add-permission `
        --function-name $functionName `
        --statement-id AllowAPIGatewayInvoke `
        --action lambda:InvokeFunction `
        --principal apigateway.amazonaws.com `
        --region $region 2>&1 | Out-Null
    
    Write-Host "✓ Permission added" -ForegroundColor Green
} else {
    Write-Host "✓ Permissions already configured" -ForegroundColor Green
}

# Step 5: Get deployment info
Write-Host "`n[5/5] Retrieving deployment information..." -ForegroundColor Yellow

$apiUrl = "https://$apiId.execute-api.$region.amazonaws.com"

Write-Host "`n" -ForegroundColor Cyan
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║          🎉 DEPLOYMENT SUCCESSFUL 🎉                      ║" -ForegroundColor Green
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host "`n📍 API Gateway URL: $apiUrl" -ForegroundColor Cyan
Write-Host "📍 Lambda Function: $functionName" -ForegroundColor Cyan
Write-Host "📍 Region: $region" -ForegroundColor Cyan
Write-Host "`n" -ForegroundColor Cyan

# Test endpoints
Write-Host "🧪 Testing API endpoints..." -ForegroundColor Yellow
Start-Sleep -Seconds 2

$testUrl = "$apiUrl/"
Write-Host "`nGET $testUrl"
try {
    $response = Invoke-WebRequest -Uri $testUrl -Method GET -ErrorAction Stop
    Write-Host "✓ Status: 200" -ForegroundColor Green
    Write-Host ($response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 2)
} catch {
    Write-Host "⚠️  First invoke - may be cold start. Retrying in 3s..." -ForegroundColor Yellow
    Start-Sleep -Seconds 3
    try {
        $response = Invoke-WebRequest -Uri $testUrl -Method GET -ErrorAction Stop
        Write-Host "✓ Status: 200" -ForegroundColor Green
        Write-Host ($response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 2)
    } catch {
        Write-Host "❌ Error: $_" -ForegroundColor Red
    }
}

# More tests
$testUrl2 = "$apiUrl/api/hello/world"
Write-Host "`nGET $testUrl2"
try {
    $response = Invoke-WebRequest -Uri $testUrl2 -Method GET -ErrorAction Stop
    Write-Host "✓ Status: 200" -ForegroundColor Green
    Write-Host ($response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 2)
} catch {
    Write-Host "❌ Error: $_" -ForegroundColor Red
}

Write-Host "`n✅ Deployment complete! Start testing with: $apiUrl" -ForegroundColor Green
Write-Host "`n📚 Next steps:" -ForegroundColor Yellow
Write-Host "  1. Check CloudWatch Logs: aws logs tail /aws/lambda/$functionName --follow --region $region" -ForegroundColor Gray
Write-Host "  2. Invoke function: aws lambda invoke --function-name $functionName --region $region response.json" -ForegroundColor Gray
Write-Host "  3. View logs: Get-Content response.json" -ForegroundColor Gray
