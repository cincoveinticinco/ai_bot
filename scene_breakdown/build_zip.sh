# al inicio
set -euo pipefail
LAMBDA_NAME="scene_breakdown"
FILES=("main.py" "prompts" "responses")

echo "🧹 Limpiando archivos anteriores..."
rm -rf lambda_build "$LAMBDA_NAME.zip"

echo "📁 Creando carpeta lambda_build..."
mkdir lambda_build

echo "🐳 Instalando dependencias en entorno compatible con Lambda..."
docker run --rm -v "$PWD":/var/task public.ecr.aws/sam/build-python3.11 \
  pip install --platform manylinux2014_x86_64 --implementation cp \
  --python-version 3.11 --only-binary=:all: \
  -r requirements.txt -t lambda_build

echo "📦 Copiando archivos fuente y recursos..."
for file in "${FILES[@]}"; do
  cp -r "$file" lambda_build/
done

echo "🗜️ Generando ZIP..."
cd lambda_build
zip -r9 ../$LAMBDA_NAME.zip .
cd ..

echo "✅ ZIP generado: $LAMBDA_NAME.zip"
