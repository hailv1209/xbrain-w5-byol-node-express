# AWS CLI & Lambda Management Guide cho Windows

## Mục tiêu
Hướng dẫn chi tiết để quản lý, kiểm tra, và cập nhật Lambda function trên Windows bằng AWS CLI hoặc AWS Console.

---

## PHẦN 1: CẤP HÌNH AWS CLI trên Windows

### 1.1 Cài AWS CLI
```powershell
# Cách 1: Download installer (easiest)
# Truy cập: https://aws.amazon.com/cli/
# Download AWS CLI MSI Installer for Windows
# Chạy installer (next, next, finish)

# Cách 2: Dùng Chocolatey (nếu đã cài)
choco install awscli

# Cách 3: Dùng pip (nếu đã cài Python)
pip install awscli
```

### 1.2 Cấu hình Credentials
```powershell
# Mở PowerShell hoặc CMD
aws configure

# Hoặc:
aws configure set aws_access_key_id "YOUR_ACCESS_KEY"
aws configure set aws_secret_access_key "YOUR_SECRET_KEY"
aws configure set region "us-west-2"
aws configure set output "json"

# Kiểm tra xem đã configure chưa
aws sts get-caller-identity
# Output: { "UserId": "...", "Account": "379353384462", "Arn": "..." }
```

### 1.3 Xóa/Reset Credentials (nếu cần)
```powershell
# Credentials lưu tại:
$env:USERPROFILE\.aws\credentials
$env:USERPROFILE\.aws\config

# Xóa và cấu hình lại
Remove-Item "$env:USERPROFILE\.aws\credentials"
Remove-Item "$env:USERPROFILE\.aws\config"
aws configure  # Cấu hình lại
```

---

## PHẦN 2: QUẢN LÝ LAMBDA FUNCTION

### 2.1 Xem thông tin Lambda function
```powershell
# Lấy thông tin cơ bản
aws lambda get-function `
  --function-name byol-node-express `
  --region us-west-2

# Lấy cấu hình
aws lambda get-function-configuration `
  --function-name byol-node-express `
  --region us-west-2

# Lấy policy
aws lambda get-policy `
  --function-name byol-node-express `
  --region us-west-2
```

### 2.2 Invoke Lambda (test function)
```powershell
# Invoke với payload trống
aws lambda invoke `
  --function-name byol-node-express `
  --region us-west-2 `
  --payload '{}' `
  response.json

# Xem response
Get-Content response.json | ConvertFrom-Json

# Invoke với test data
aws lambda invoke `
  --function-name byol-node-express `
  --region us-west-2 `
  --payload '{"test":"data"}' `
  response.json

# Invoke async (không chờ response)
aws lambda invoke `
  --function-name byol-node-express `
  --invocation-type Event `
  --region us-west-2 `
  --payload '{}' `
  response.json
```

### 2.3 Update Lambda Function

#### Update code (ZIP file)
```powershell
# Step 1: Zip code
Compress-Archive -Path .\ -DestinationPath function.zip -Force

# Step 2: Update
aws lambda update-function-code `
  --function-name byol-node-express `
  --zip-file "fileb://function.zip" `
  --region us-west-2

# Wait for update
Start-Sleep -Seconds 3

# Verify
aws lambda get-function `
  --function-name byol-node-express `
  --region us-west-2 `
  --query 'Configuration.LastModified'
```

#### Update configuration (handler, timeout, memory, etc.)
```powershell
# Change memory
aws lambda update-function-configuration `
  --function-name byol-node-express `
  --memory-size 1024 `
  --region us-west-2

# Change timeout
aws lambda update-function-configuration `
  --function-name byol-node-express `
  --timeout 30 `
  --region us-west-2

# Change environment variables
aws lambda update-function-configuration `
  --function-name byol-node-express `
  --environment 'Variables={NODE_ENV=production,DEBUG=false}' `
  --region us-west-2

# Change handler
aws lambda update-function-configuration `
  --function-name byol-node-express `
  --handler "lambda.handler" `
  --region us-west-2
```

### 2.4 Xem Lambda logs (CloudWatch)
```powershell
# Get log streams
aws logs describe-log-streams `
  --log-group-name /aws/lambda/byol-node-express `
  --region us-west-2 `
  --order-by LastEventTime `
  --descending

# Get log events từ stream
$streamName = "2026/05/15/[\$LATEST]d06ab85a807c4e718a2682f69d866773"
aws logs get-log-events `
  --log-group-name /aws/lambda/byol-node-express `
  --log-stream-name $streamName `
  --region us-west-2

# Tail logs (real-time) - dùng AWS CloudWatch CLI (không phải AWS CLI core)
# Hoặc dùng AWS Console
```

---

## PHẦN 3: API GATEWAY

### 3.1 Xem API Gateway info
```powershell
# Lấy API ID
$apiId = "tvh58h1kz3"
aws apigatewayv2 get-apis --region us-west-2

# Lấy stage
aws apigatewayv2 get-stages `
  --api-id $apiId `
  --region us-west-2

# Xem target (Lambda)
aws apigatewayv2 get-integrations `
  --api-id $apiId `
  --region us-west-2
```

### 3.2 Update API Gateway
```powershell
# Change integration target (gọi Lambda function khác)
aws apigatewayv2 update-integration `
  --api-id $apiId `
  --integration-id "your-integration-id" `
  --target "arn:aws:lambda:us-west-2:379353384462:function:new-function-name" `
  --region us-west-2
```

---

## PHẦN 4: IAM ROLES & PERMISSIONS

### 4.1 Xem IAM role
```powershell
aws iam get-role --role-name byol-node-express-role

# Xem attached policies
aws iam list-attached-role-policies `
  --role-name byol-node-express-role

# Xem inline policies
aws iam list-role-policies `
  --role-name byol-node-express-role

# Get policy details
aws iam get-role-policy `
  --role-name byol-node-express-role `
  --policy-name policy-name
```

### 4.2 Thêm permissions
```powershell
# Thêm permission cho API Gateway invoke
aws lambda add-permission `
  --function-name byol-node-express `
  --statement-id AllowAPIGatewayInvoke `
  --action lambda:InvokeFunction `
  --principal apigateway.amazonaws.com `
  --region us-west-2

# Thêm permission cho DynamoDB access
aws iam put-role-policy `
  --role-name byol-node-express-role `
  --policy-name DynamoDBAccess `
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "dynamodb:*",
      "Resource": "*"
    }]
  }'
```

---

## PHẦN 5: MONITORING & METRICS

### 5.1 Xem metrics
```powershell
# Get invocations count
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Invocations `
  --dimensions Name=FunctionName,Value=byol-node-express `
  --start-time (Get-Date).AddHours(-1) `
  --end-time (Get-Date) `
  --period 3600 `
  --statistics Sum

# Get errors
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Errors `
  --dimensions Name=FunctionName,Value=byol-node-express `
  --start-time (Get-Date).AddHours(-1) `
  --end-time (Get-Date) `
  --period 3600 `
  --statistics Sum

# Get duration
aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Duration `
  --dimensions Name=FunctionName,Value=byol-node-express `
  --start-time (Get-Date).AddHours(-1) `
  --end-time (Get-Date) `
  --period 3600 `
  --statistics Average,Maximum
```

### 5.2 Set alarms
```powershell
# Alert khi có errors
aws cloudwatch put-metric-alarm `
  --alarm-name "Lambda-Errors" `
  --alarm-description "Alert when Lambda has errors" `
  --metric-name Errors `
  --namespace AWS/Lambda `
  --statistic Sum `
  --period 300 `
  --evaluation-periods 1 `
  --threshold 1 `
  --comparison-operator GreaterThanOrEqualToThreshold `
  --dimensions Name=FunctionName,Value=byol-node-express `
  --alarm-actions arn:aws:sns:us-west-2:379353384462:NotificationTopic
```

---

## PHẦN 6: DEPLOYMENT & VERSIONING

### 6.1 Publish version
```powershell
# Publish current version
aws lambda publish-version `
  --function-name byol-node-express `
  --description "Version 1.0" `
  --region us-west-2

# List versions
aws lambda list-versions-by-function `
  --function-name byol-node-express `
  --region us-west-2
```

### 6.2 Create alias (for different stages)
```powershell
# Create PROD alias
aws lambda create-alias `
  --function-name byol-node-express `
  --name prod `
  --function-version 1 `
  --region us-west-2

# Create DEV alias
aws lambda create-alias `
  --function-name byol-node-express `
  --name dev `
  --function-version \$LATEST `
  --region us-west-2

# Invoke specific alias
aws lambda invoke `
  --function-name byol-node-express:prod `
  --region us-west-2 `
  response.json
```

---

## PHẦN 7: CLEANUP & DELETION

### 7.1 Delete Lambda function
```powershell
# Delete function (⚠️ KHÔNG THỂ HOÀN TÁC)
aws lambda delete-function `
  --function-name byol-node-express `
  --region us-west-2
```

### 7.2 Delete API Gateway
```powershell
$apiId = "tvh58h1kz3"
aws apigatewayv2 delete-api `
  --api-id $apiId `
  --region us-west-2
```

### 7.3 Delete IAM role
```powershell
# Trước tiên, xóa attached policies
aws iam detach-role-policy `
  --role-name byol-node-express-role `
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Xóa inline policies
aws iam delete-role-policy `
  --role-name byol-node-express-role `
  --policy-name policy-name

# Sau cùng, xóa role
aws iam delete-role `
  --role-name byol-node-express-role
```

---

## PHẦN 8: TROUBLESHOOTING

### 8.1 Function không invoke được
```powershell
# Check permissions
aws lambda get-policy --function-name byol-node-express --region us-west-2

# Check handler format
aws lambda get-function-configuration --function-name byol-node-express --region us-west-2

# Check code (lấy lần deploy gần nhất)
# Kiểm tra trong CloudWatch logs
```

### 8.2 Cold start quá lâu
```powershell
# Tăng memory (= tăng CPU power)
aws lambda update-function-configuration `
  --function-name byol-node-express `
  --memory-size 2048 `
  --region us-west-2

# Provisioned Concurrency (giữ warm instances ready)
aws lambda put-provisioned-concurrency-config `
  --function-name byol-node-express:prod `
  --provisioned-concurrent-executions 10 `
  --region us-west-2

# Check current metrics
aws lambda get-provisioned-concurrency-config `
  --function-name byol-node-express:prod `
  --region us-west-2
```

### 8.3 API Gateway 502 Bad Gateway
```powershell
# Check CloudWatch logs (Lambda execution logs)
# Check HTTP status codes
# Verify handler format
# Verify Lambda has permission from API Gateway

# Re-add permission nếu bị mất
aws lambda add-permission `
  --function-name byol-node-express `
  --statement-id AllowAPIGatewayInvoke `
  --action lambda:InvokeFunction `
  --principal apigateway.amazonaws.com `
  --region us-west-2
```

---

## PHẦN 9: HELPFUL SCRIPTS

### 9.1 Get full function info
```powershell
$functionName = "byol-node-express"
$region = "us-west-2"

Write-Host "=== LAMBDA FUNCTION INFO ===" -ForegroundColor Cyan
$func = aws lambda get-function-configuration --function-name $functionName --region $region | ConvertFrom-Json
Write-Host "Name: $($func.FunctionName)"
Write-Host "Runtime: $($func.Runtime)"
Write-Host "Handler: $($func.Handler)"
Write-Host "Memory: $($func.MemorySize) MB"
Write-Host "Timeout: $($func.Timeout) seconds"
Write-Host "Last Modified: $($func.LastModified)"
Write-Host "Code Size: $($func.CodeSize) bytes"

Write-Host "`n=== API GATEWAY INFO ===" -ForegroundColor Cyan
$apis = aws apigatewayv2 get-apis --region $region | ConvertFrom-Json
$api = $apis.Items | Where-Object { $_.Name -like "*node-express*" }
Write-Host "API ID: $($api.ApiId)"
Write-Host "API Name: $($api.Name)"
Write-Host "URL: https://$($api.ApiId).execute-api.$region.amazonaws.com"

Write-Host "`n=== RECENT ERRORS ===" -ForegroundColor Cyan
$errors = aws cloudwatch get-metric-statistics `
  --namespace AWS/Lambda `
  --metric-name Errors `
  --dimensions Name=FunctionName,Value=$functionName `
  --start-time (Get-Date).AddHours(-1) `
  --end-time (Get-Date) `
  --period 3600 `
  --statistics Sum `
  --region $region | ConvertFrom-Json
Write-Host "Errors (last hour): $($errors.Datapoints[0].Sum ?? 0)"
```

### 9.2 Monitor function in real-time
```powershell
# PowerShell script để monitor mỗi 10 giây
$functionName = "byol-node-express"
$region = "us-west-2"

while ($true) {
    Clear-Host
    Write-Host "🔄 Lambda Function Monitor - Updated: $(Get-Date)" -ForegroundColor Green
    
    $stats = aws cloudwatch get-metric-statistics `
      --namespace AWS/Lambda `
      --metric-name Invocations `
      --dimensions Name=FunctionName,Value=$functionName `
      --start-time (Get-Date).AddMinutes(-5) `
      --end-time (Get-Date) `
      --period 60 `
      --statistics Sum `
      --region $region | ConvertFrom-Json
    
    Write-Host "Invocations (5 min): $($stats.Datapoints | Measure-Object -Property Sum -Sum | Select-Object -ExpandProperty Sum)"
    
    $errors = aws cloudwatch get-metric-statistics `
      --namespace AWS/Lambda `
      --metric-name Errors `
      --dimensions Name=FunctionName,Value=$functionName `
      --start-time (Get-Date).AddMinutes(-5) `
      --end-time (Get-Date) `
      --period 60 `
      --statistics Sum `
      --region $region | ConvertFrom-Json
    
    Write-Host "Errors (5 min): $($errors.Datapoints | Measure-Object -Property Sum -Sum | Select-Object -ExpandProperty Sum)"
    
    Start-Sleep -Seconds 10
}
```

---

## PHẦN 10: AWS CONSOLE ALTERNATIVE (Graphical)

Nếu không muốn dùng AWS CLI, bạn có thể dùng AWS Console:

### 10.1 Xem Lambda function
1. Truy cập: https://console.aws.amazon.com/lambda/
2. Chọn region: **us-west-2**
3. Tìm function: **byol-node-express**
4. Xem tabs: Code, Configuration, Monitor, Logs

### 10.2 Update code
1. Click "Upload from .zip file"
2. Select file: `function.zip`
3. Click "Deploy"

### 10.3 Update configuration
1. Click "Edit" in Configuration tab
2. Change: Memory, Timeout, Handler, etc.
3. Click "Save"

### 10.4 Monitor
1. Click "Monitor" tab
2. Xem graphs: Invocations, Errors, Duration, etc.
3. Click "View logs in CloudWatch"

---

## CHEATSHEET (copy-paste)

```powershell
# Cấu hình (chỉ cần 1 lần)
aws configure

# Invoke test
aws lambda invoke --function-name byol-node-express --region us-west-2 --payload '{}' response.json

# Update code
Compress-Archive -Path .\ -DestinationPath function.zip -Force
aws lambda update-function-code --function-name byol-node-express --zip-file "fileb://function.zip" --region us-west-2

# Xem logs
aws logs describe-log-streams --log-group-name /aws/lambda/byol-node-express --region us-west-2

# Tăng memory
aws lambda update-function-configuration --function-name byol-node-express --memory-size 1024 --region us-west-2

# Delete
aws lambda delete-function --function-name byol-node-express --region us-west-2
```

---

## Liên hệ hỗ trợ
- AWS CLI docs: https://docs.aws.amazon.com/cli/
- Lambda docs: https://docs.aws.amazon.com/lambda/
- AWS Console: https://console.aws.amazon.com/
