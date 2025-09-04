#!/bin/bash

echo "🧹 Limpiando archivos anteriores..."
rm -rf lambda_build question_analysis_lambda.zip

echo "📁 Creando carpeta lambda_build..."
mkdir lambda_build

echo "🐳 Instalando dependencias en entorno compatible con Lambda..."
docker run --rm -v "$PWD":/var/task public.ecr.aws/sam/build-python3.11 \
  pip install --platform manylinux2014_x86_64 --implementation cp \
  --python-version 3.11 --only-binary=:all: \
  -r requirements.txt -t lambda_build

echo "📦 Copiando archivos fuente y recursos..."
cp analyze_question.py lambda_build/
cp -r prompts lambda_build/

echo "🗜️ Generando ZIP..."
cd lambda_build
zip -r9 ../question_analysis_lambda.zip .
cd ..

echo "✅ ZIP generado: question_analysis_lambda.zip"
