FROM public.ecr.aws/lambda/python:3.13 AS builder

WORKDIR ${LAMBDA_TASK_ROOT}

# Install system dependencies for owlready2 and other packages
RUN yum update -y && \
    yum install -y gcc gcc-c++ make && \
    yum clean all

COPY requirements.txt .

# Upgrade pip and install dependencies with verbose output
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt --target . --verbose

FROM public.ecr.aws/lambda/python:3.13

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder ${LAMBDA_TASK_ROOT} .

COPY lambda_function.py ./
COPY agent/ ./agent/
COPY core/ ./core/

CMD ["lambda_function.lambda_handler"]