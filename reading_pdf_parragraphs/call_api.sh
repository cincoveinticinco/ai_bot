#!/usr/bin/env bash
set -euo pipefail

export API_ID=g85fx95qsk
export AWS_REGION=us-east-1
export API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com"
echo "$API_ENDPOINT"

curl -s -X POST "$API_ENDPOINT/prod/extract_paragraphs" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json | python3 -m json.tool