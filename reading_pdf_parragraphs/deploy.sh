#!/usr/bin/env bash
set -euo pipefail

aws lambda get-function --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}" >/dev/null 2>&1 || {
  echo "❌ La Lambda '${FUNCTION_NAME}' no existe en ${AWS_REGION}. Revisa FUNCTION_NAME."
  exit 1
}

# === Config ===
# (1) Cargar .env si existe (debe definir: ACCOUNT_ID, AWS_REGION, REPO, FUNCTION_NAME)
if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

# (2) Validar variables requeridas
: "${ACCOUNT_ID:?Debes exportar ACCOUNT_ID o definirlo en .env}"
: "${AWS_REGION:?Debes exportar AWS_REGION o definirlo en .env}"
: "${REPO:?Debes exportar REPO o definirlo en .env}"
: "${FUNCTION_NAME:?Debes exportar FUNCTION_NAME o definirlo en .env}"

# Permite pasar el tag como 1er argumento (por defecto lambda-v1)
TAG="${1:-lambda-v1}"

echo "==> Build de imagen (${TAG})"
# Fuerza builder heredado (no BuildKit) para obtener manifest simple aceptado por Lambda
export DOCKER_BUILDKIT=0
docker build -t "pdf-paragraphs:${TAG}" .

echo "==> Login a ECR"
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "==> Tag y Push a ECR"
docker tag "pdf-paragraphs:${TAG}" "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO}:${TAG}"
docker push "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO}:${TAG}"

echo "==> Update de Lambda"
aws lambda update-function-code \
  --function-name "${FUNCTION_NAME}" \
  --image-uri "${ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${REPO}:${TAG}" \
  --region "${AWS_REGION}" >/dev/null

aws lambda wait function-updated --function-name "${FUNCTION_NAME}" --region "${AWS_REGION}"

echo "✅ Deploy listo: ${FUNCTION_NAME} -> ${TAG}"
