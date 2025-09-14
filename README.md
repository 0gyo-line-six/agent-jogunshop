# 에이전트 조군샵 (AWS Lambda)

조군샵 고객 상담을 위한 AI 에이전트 시스템입니다. AWS Lambda 환경에서 동작하며, S3에서 온톨로지 파일을 로드합니다.

## ✨ 주요 기능

- **상품 에이전트**: 상품 정보, 가격, 재고, 옵션 조회
- **배송 에이전트**: 배송 정책, 배송 상태 안내
- **일반 에이전트**: 기타 고객 문의 처리
- **자동 라우팅**: 사용자 요청을 적절한 에이전트로 자동 분배

## 🏗️ 아키텍처

```
Channel.io Webhook → AWS Lambda → Agent Router → Specialized Agents
                         ↓
                   S3 (ontology.owl) → Ontology Manager
                         ↓
                   DynamoDB (chat states) + Step Functions (scheduling)
```

## ⚙️ 환경 설정

### 필수 환경 변수

#### Azure OpenAI
```bash
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_DEPLOYMENT_ID=your-deployment-name
```

#### Channel API
```bash
CHANNEL_API_BASE_URL=https://api.channel.io
CHANNEL_ACCESS_KEY=your-access-key
CHANNEL_ACCESS_SECRET=your-access-secret
```

#### AWS 서비스
```bash
AWS_REGION=ap-northeast-2
S3_BUCKET_NAME=jogunshop-bucket
ONTOLOGY_S3_KEY=ontology.owl
DYNAMODB_TABLE_NAME=jogunshop-chat-states
STATE_MACHINE_ARN=arn:aws:states:ap-northeast-2:123456789012:stateMachine:JogunshopChatProcessor
```

#### 시스템 설정
```bash
DSPY_CACHE_DIR=/tmp/dspy_cache
```

## 🚀 배포 방법 (최적화됨)

### 1. 기존 빌드 완전 정리 (권장)
```bash
# ECR의 모든 이미지 삭제 (초기화)
aws ecr list-images --repository-name agent-jogunshop --query 'imageIds[*]' --output json | \
jq -r '.[] | "imageDigest=" + .imageDigest' | \
xargs -I {} aws ecr batch-delete-image --repository-name agent-jogunshop --image-ids {} 2>/dev/null || true

# Account ID 자동 확인
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account ID: $ACCOUNT_ID"

# 로컬 이미지와 캐시 완전 정리
docker rmi agent-jogunshop:latest 2>/dev/null || true
docker rmi $ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/agent-jogunshop:* 2>/dev/null || true
docker system prune -af
docker builder prune -af
```

### 2. Docker 이미지 빌드
```bash
# buildx 비활성화로 단일 아키텍처 이미지 강제 생성
export DOCKER_BUILDKIT=0
docker build --pull --no-cache -t agent-jogunshop .

# 빌드된 이미지 아키텍처 확인
docker image inspect agent-jogunshop:latest --format '{{.Architecture}}'
```

### 3. ECR에 이미지 푸시
```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com

# 고유한 태그로 이미지 푸시 (Image Manifest 충돌 방지)
IMAGE_TAG="v$(date +%Y%m%d-%H%M%S)"
docker tag agent-jogunshop:latest $ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/agent-jogunshop:$IMAGE_TAG
docker push $ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/agent-jogunshop:$IMAGE_TAG
```

### 4. Lambda 함수 업데이트
```bash
# 함수가 있는 경우
FULL_IMAGE_URI="$ACCOUNT_ID.dkr.ecr.ap-northeast-2.amazonaws.com/agent-jogunshop:$IMAGE_TAG"
aws lambda update-function-code \
  --function-name agent-jogunshop \
  --image-uri $FULL_IMAGE_URI
```

## 🔐 IAM 권한 설정

Lambda 실행 역할에 다음 권한이 필요합니다:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject"
            ],
            "Resource": "arn:aws:s3:::jogunshop-bucket/*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem"
            ],
            "Resource": "arn:aws:dynamodb:ap-northeast-2:*:table/jogunshop-chat-states"
        },
        {
            "Effect": "Allow",
            "Action": [
                "states:StartExecution",
                "states:ListExecutions",
                "states:StopExecution"
            ],
            "Resource": "arn:aws:states:ap-northeast-2:*:stateMachine:JogunshopChatProcessor"
        }
    ]
}
```

## 📁 프로젝트 구조

```
agent-jogunshop/
├── agent/                      # 에이전트 모듈
│   ├── delivery_agent.py      # 배송 관련 처리
│   ├── general_agent.py       # 일반 문의 처리
│   ├── product_agent.py       # 상품 정보 처리
│   └── router.py              # 에이전트 라우팅
├── core/                       # 핵심 모듈
│   ├── config.py              # 설정 관리
│   ├── ontology_manager.py    # 온톨로지 관리 (S3 통합)
│   └── webhook.py             # 웹훅 처리
├── data/                       # 데이터 파일
│   └── delivery_policy.txt    # 배송 정책
├── lambda_function.py          # Lambda 핸들러
├── Dockerfile                  # 컨테이너 이미지
└── requirements.txt            # Python 의존성
```

## 🧪 테스트

### Lambda 테스트
```bash
# 테스트 이벤트로 함수 호출
aws lambda invoke \
  --function-name jogunshop-agent \
  --payload '{"type": "message", "entity": {"chatId": "test", "plainText": "안녕하세요", "personType": "user"}}' \
  response.json
```

## 📊 모니터링

### CloudWatch 로그 확인
```bash
# 로그 그룹 확인
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/jogunshop-agent

# 최신 로그 확인
aws logs tail /aws/lambda/jogunshop-agent --follow
```

### 주요 메트릭
- 함수 실행 시간 (일반적으로 5-30초)
- 메모리 사용량 (권장: 1024MB)
- 오류 발생률 (목표: < 1%)
- 온톨로지 로딩 시간 (초기화 시)

## 🔧 트러블슈팅

### 온톨로지 로딩 실패
1. S3 버킷 이름과 파일 경로 확인
2. IAM 권한 확인 (S3 GetObject)
3. 온톨로지 파일 형식 및 크기 확인

### DSPy 초기화 실패
1. Azure OpenAI 환경 변수 확인
2. API 키 유효성 확인
3. 모델 배포 상태 확인

### 메모리/타임아웃 오류
1. Lambda 메모리를 1536MB로 증가
2. 타임아웃을 15분으로 설정
3. 대용량 온톨로지의 경우 캐싱 최적화

## 📈 성능 최적화

- 프로비저닝된 동시성 사용
- 메모리 크기 최적화
- S3 Transfer Acceleration 활용
- 온톨로지 파일 압축

---

**중요**: 이 시스템은 AWS Lambda 환경에서만 동작하도록 설계되었습니다. 로컬 개발 환경에서는 S3 연결이 필수입니다.
