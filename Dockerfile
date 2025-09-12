FROM public.ecr.aws/lambda/python:3.11 AS builder

WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies - try yum first for Amazon Linux
RUN yum update -y && \
    yum install -y gcc gcc-c++ make java-11-amazon-corretto-headless && \
    yum clean all

COPY requirements.txt .

# Upgrade pip and install dependencies with verbose output
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --target . --verbose

FROM public.ecr.aws/lambda/python:3.11

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder ${LAMBDA_TASK_ROOT} .

COPY lambda_function.py ./
COPY agent/ ./agent/
COPY core/ ./core/

CMD ["lambda_function.lambda_handler"]