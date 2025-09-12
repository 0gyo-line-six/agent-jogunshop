FROM public.ecr.aws/lambda/python:3.13 AS builder

WORKDIR ${LAMBDA_TASK_ROOT}

# 빌드에 필요한 도구들 설치 (Rust와 C 컴파일러 포함)
RUN dnf update -y && \
    dnf install -y gcc gcc-c++ make cmake git tar gzip && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y && \
    source ~/.cargo/env && \
    dnf clean all

# Rust 환경 변수 설정
ENV PATH="/root/.cargo/bin:${PATH}"

COPY requirements.txt .

# 더 안정적인 pip 설치 옵션 사용
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --verbose --compile --timeout 300 -r requirements.txt --target .

FROM public.ecr.aws/lambda/python:3.13

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder ${LAMBDA_TASK_ROOT} .

COPY lambda_function.py ./
COPY agent/ ./agent/
COPY core/ ./core/
COPY data/ ./data/

CMD ["lambda_function.lambda_handler"]