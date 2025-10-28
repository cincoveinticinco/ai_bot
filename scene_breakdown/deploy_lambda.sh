#!/bin/bash

# CONFIGURACIÓN
LAMBDA_NAME="scene_breakdown"
ZIP_FILE="${LAMBDA_NAME}.zip"
PY_MAIN="main"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ROLE="lambda_basic_execution"
ROLE_ARN="arn:aws:iam::$ACCOUNT_ID:role/$ROLE"
RUNTIME="python3.11"
HANDLER="$PY_MAIN.lambda_handler"
TIMEOUT=400
# Obtener OPENAI_API_KEY desde .env
if [ -f ".env" ]; then
  OPENAI_API_KEY=$(grep '^OPENAI_API_KEY=' .env | cut -d '=' -f2-)
else
  echo "❌ Archivo .env no encontrado. Abortando."
  exit 1
fi
ENV_VARS="OPENAI_API_KEY=$OPENAI_API_KEY"

# ✅ Verificar que el ZIP exista, si no, ejecutar build
if [ ! -f "$ZIP_FILE" ]; then
  echo "📦 No se encontró $ZIP_FILE. Ejecutando build_zip.sh..."
  ./build_zip.sh
  if [ $? -ne 0 ]; then
    echo "❌ Falló la generación del ZIP. Abortando."
    exit 1
  fi
else
  echo "📦 ZIP encontrado: $ZIP_FILE"
fi

# ✅ Verifica si la función Lambda ya existe
echo "🔍 Verificando existencia de Lambda $LAMBDA_NAME..."
aws lambda get-function --function-name "$LAMBDA_NAME" > /dev/null 2>&1

if [ $? -ne 0 ]; then
  echo "🚀 Lambda no existe. Creándola..."
  aws lambda create-function \
    --function-name "$LAMBDA_NAME" \
    --runtime "$RUNTIME" \
    --role "$ROLE_ARN" \
    --handler "$HANDLER" \
    --timeout "$TIMEOUT" \
    --environment "Variables={$ENV_VARS}" \
    --zip-file fileb://$(pwd)/"$ZIP_FILE"
else
  echo "🔄 Lambda ya existe. Actualizando ZIP..."
  aws lambda update-function-code \
    --function-name "$LAMBDA_NAME" \
    --zip-file fileb://$(pwd)/"$ZIP_FILE"

  echo "⚙️ Asegurando configuración del handler y runtime..."
  aws lambda update-function-configuration \
    --function-name "$LAMBDA_NAME" \
    --handler "$HANDLER" \
    --runtime "$RUNTIME" \
    --timeout "$TIMEOUT" \
    --environment "Variables={$ENV_VARS}"
fi

# 🧹 LIMPIEZA FINAL
echo "🧹 Limpiando archivos temporales..."
rm -rf lambda_build "$ZIP_FILE"

echo "✅ Lambda $LAMBDA_NAME desplegada y archivos eliminados."