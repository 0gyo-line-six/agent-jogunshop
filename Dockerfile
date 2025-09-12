FROM public.ecr.aws/lambda/python:3.13 AS builder

WORKDIR ${LAMBDA_TASK_ROOT}

COPY requirements.txt .

RUN pip install --no-cache-dir -v -r requirements.txt --target .

FROM public.ecr.aws/lambda/python:3.13

WORKDIR ${LAMBDA_TASK_ROOT}

COPY --from=builder ${LAMBDA_TASK_ROOT} .

COPY lambda_function.py ./
COPY agent/ ./agent/
COPY core/ ./core/
COPY data/ ./data/

CMD ["lambda_function.lambda_handler"]