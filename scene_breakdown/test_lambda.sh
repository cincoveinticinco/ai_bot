LAMBDA_NAME="scene_breakdown"
echo "📦 VAMOS A PROBAR LA LAMBDA..."

aws lambda invoke \
  --function-name $LAMBDA_NAME \
  --payload fileb://$(pwd)/events/event.json \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json
