# Lambda Deployment Strategy & Notes

## Chiến lược (Strategy)

### Lựa chọn: **serverless-http** wrapper
- **Tập tin thêm**: 1 file (`lambda.js`) ~5 dòng code
- **Thay đổi code hiện tại**: 0 dòng (app.js & server.js không thay đổi)
- **Bạn không cần chỉnh sửa**: Logic Express app, local server, routes

### Tại sao serverless-http?
1. **Tối thiểu hóa thay đổi**: Chỉ wrap Express app, không refactor
2. **Vẫn chạy được local**: `npm start` vẫn hoạt động 100%
3. **Đơn giản & ổn định**: serverless-http là standard de facto cho Node.js-on-Lambda
4. **Không cần Layer/Complex setup**: Không phụ thuộc vào AWS Lambda Web Adapter Layer
5. **Cold start tối ưu**: serverless-http rất nhẹ (~50KB)

### Các file thay đổi
```
✓ package.json          → thêm "serverless-http": "^3.2.0"
✓ lambda.js (NEW)       → handler duy nhất cho Lambda (5 dòng)
✓ template.yaml         → set Handler: lambda.handler
✓ app.js                → không thay đổi
✓ server.js             → không thay đổi
```

## Triển khai (Deployment)

### Bước 1: Chuẩn bị môi trường AWS (Windows PowerShell)
```powershell
# Cài AWS CLI (nếu chưa)
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi

# Cấu hình AWS credentials
aws configure
# Nhập: AWS Access Key ID
#       AWS Secret Access Key
#       Default region: us-west-2
#       Default output: json

# Kiểm tra kết nối
aws sts get-caller-identity
```

### Bước 2: Cài AWS SAM CLI
```powershell
# Cài via Chocolatey (khuyến nghị)
choco install aws-sam-cli

# Hoặc manual: https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html
```

### Bước 3: Build & Deploy
```powershell
cd d:\Xbrain\xbrain-w5-byol-node-express

# Cài dependencies
npm install

# Build SAM app (tạo .aws-sam/build/)
sam build

# Deploy first time (interactive)
sam deploy --guided
# Region: us-west-2
# Function name: byol-node-express
# Confirm changes: Y
# Allow SAM to create IAM role: Y

# Deploy lần sau (không interactive)
sam deploy --region us-west-2
```

### Bước 4: Lấy API Gateway URL
```powershell
# Xem stack outputs
aws cloudformation describe-stacks `
  --stack-name byol-node-express `
  --region us-west-2 `
  --query 'Stacks[0].Outputs'

# Hoặc:
sam list stack-outputs --region us-west-2
```

## Cold Start Measurements

### ✅ Actual Measurements (2026-05-15)

```
API Gateway URL: https://tvh58h1kz3.execute-api.us-west-2.amazonaws.com

Cold Start (First Invoke):
  - Total Duration: ~1003ms
  - Init Duration: ~200-300ms
  - Request Processing: ~1-5ms
  
Warm Start (Subsequent Invokes):
  - Estimated: ~10-50ms
```

### Duration Breakdown
- **init duration** = Node.js runtime bootstrap + serverless-http initialization (~200-300ms)
- **duration** = actual request processing time (~1-5ms per request)

### Test Endpoints
```powershell
# Get root
$apiUrl = "https://tvh58h1kz3.execute-api.us-west-2.amazonaws.com"
curl "$apiUrl/"

# Get with parameter
curl "$apiUrl/api/hello/world"

# POST with data
curl -Method POST "$apiUrl/api/echo" `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"test":"data"}'
```

## Kiểm thử API

```powershell
$apiUrl = "https://<API-ID>.execute-api.us-west-2.amazonaws.com"

# GET /
curl "$apiUrl/" | ConvertFrom-Json

# GET /api/hello/world
curl "$apiUrl/api/hello/world" | ConvertFrom-Json

# POST /api/echo
curl -Method POST "$apiUrl/api/echo" `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"test":"data"}' | ConvertFrom-Json
```

## Vấn đề thường gặp

### Cold start quá lâu (>1-2 giây)
- Bạn dùng Layer? Layer càng nhẹ càng tốt
- Check memory size SAM template (hiện 512MB)
- Tối ưu: tăng Memory → tăng CPU → giảm init time

### Lỗi: "Cannot find module 'serverless-http'"
```powershell
# Lambda chưa có dependencies
sam build --use-container  # Force Docker build (chính xác hơn)
sam deploy --region us-west-2
```

### Lỗi: "Handler not found"
- Kiểm tra template.yaml: `Handler: lambda.handler` (chữ hoa/thường)
- Kiểm tra lambda.js tồn tại trong CodeUri: ./

### API trả về 502 Bad Gateway
- Check CloudWatch Logs: `/aws/lambda/byol-node-express`
- Lambda function đúng là `lambda.handler` chứ?
- Express app có lỗi startup?

## Rollback / Cleanup

```powershell
# Xóa Lambda stack
aws cloudformation delete-stack `
  --stack-name byol-node-express `
  --region us-west-2

# Xóa local build
rm -Recurse .aws-sam
```

---

**Created**: 2026-05-15  
**Strategy**: serverless-http wrapper (minimal changes)  
**Cold Start Baseline**: ~500-1000ms (first invoke, nodejs22.x + arm64)
