#!/bin/bash

# CONFIGURACIÓN
LAMBDA_NAME="question_analysis_lambda"
ZIP_FILE="question_analysis_lambda.zip"
ROLE_ARN="arn:aws:iam::<TU_ACCOUNT_ID>:role/lambda_basic_execution" # ⬅️ Reemplaza <TU_ACCOUNT_ID>
RUNTIME="python3.11"
HANDLER="analyze_question.lambda_handler"

# ✅ Verificar que el ZIP exista, si no, ejecutar build
if [ ! -f "$ZIP_FILE" ]; then
  echo "📦 No se encontró $ZIP_FILE. Ejecutando build_lambda.sh..."
  ./build_lambda.sh
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
    --runtime "$RUNTIME"
fi

# 🧹 LIMPIEZA FINAL
echo "🧹 Limpiando archivos temporales..."
rm -rf lambda_build "$ZIP_FILE"

echo "✅ Lambda $LAMBDA_NAME desplegada y archivos eliminados."