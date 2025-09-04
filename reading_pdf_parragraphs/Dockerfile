# Imagen oficial de AWS Lambda para Python 3.12 en ARM64 (Graviton)
FROM public.ecr.aws/lambda/python:3.12-arm64

# Opcional: evitar bytecode y forzar logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1) Instalar dependencias en el directorio de Lambda (/var/task)
COPY requirements.txt ${LAMBDA_TASK_ROOT}/requirements.txt
RUN python -m pip install --upgrade pip \
 && pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt --target ${LAMBDA_TASK_ROOT}

# 2) Copiar tu código y artefactos al directorio de Lambda
COPY pdf_reader ${LAMBDA_TASK_ROOT}/pdf_reader
COPY ml ${LAMBDA_TASK_ROOT}/ml
COPY pdf_paragraphs_lambda.py ${LAMBDA_TASK_ROOT}/

# 3) Indicar el handler de Lambda
CMD ["pdf_paragraphs_lambda.lambda_handler"]
