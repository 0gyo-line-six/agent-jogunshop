# Lambda용 단일 스테이지 Dockerfile (Image Index 문제 방지)
FROM public.ecr.aws/lambda/python:3.13

WORKDIR ${LAMBDA_TASK_ROOT}

# 빌드에 필요한 도구들 설치
RUN dnf update -y && \
    dnf install -y gcc gcc-c++ make cmake git tar gzip && \
    dnf clean all

# 의존성 파일 복사 및 설치
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -v -r requirements.txt

# 소스 코드 복사
COPY lambda_function.py ./
COPY agent/ ./agent/
COPY core/ ./core/

# Lambda 핸들러 지정
CMD ["lambda_function.lambda_handler"]