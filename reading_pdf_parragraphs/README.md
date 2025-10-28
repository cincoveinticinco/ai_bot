Reading PDF Paragraphs — Guía de uso y debug

Servicio que extrae y clasifica párrafos desde un PDF (PyMuPDF) y se ejecuta como AWS Lambda empacada en Docker. Incluye ejecución local (Python), emulación del runtime de Lambda con Docker y exposición por API Gateway.

========================
🚀 INICIO RÁPIDO
========================

1️⃣ Clonar el repositorio y navegar al directorio
2️⃣ Ejecutar: ./run.sh start
3️⃣ Probar: ./run.sh test
4️⃣ Ver resultados en la terminal

¡Eso es todo! El script run.sh maneja Docker automáticamente.

========================
📑 ÍNDICE
========================

• 🚀 Inicio rápido
• 📁 Estructura del repo  
• ⚙️ Prerrequisitos
• 🌐 Variables de entorno
• 🐍 Uso local (Python sin Docker)
• 🐳 Ejecución con Docker (RECOMENDADO)
• ☁️ Build y deploy (AWS Lambda)
• 🧪 Testing y debugging
• 🔧 Troubleshooting

========================
Estructura del repo
========================
.
├─ pdf_reader/               # parsing del PDF
├─ ml/                       # heurísticas de clasificación
├─ pdf_paragraphs_lambda.py  # handler de Lambda
├─ requirements.txt
├─ Dockerfile
├─ deploy.sh                 # build + push + update Lambda
├─ sample.pdf                # PDF de prueba
├─ payload.json              # payload de ejemplo
└─ README.md

========================
Prerrequisitos
========================

Python 3.12

Docker instalado

AWS CLI configurada (aws configure) con permisos para ECR, Lambda y API Gateway

Cuenta AWS con Region y Role para Lambda

========================
Variables de entorno
========================

Ajusta y exporta antes de usar:

export AWS_REGION=us-east-1
export ACCOUNT_ID=<TU_ACCOUNT_ID>
export REPO=reading-pdf-paragraphs
export FUNCTION_NAME=reading-pdf-paragraphs

# Si tienes API Gateway:
export API_ID=<api_id_http>
export API_ENDPOINT="https://${API_ID}.execute-api.${AWS_REGION}.amazonaws.com"



========================
Ejecución con Docker (RECOMENDADO)
========================

El método más sencillo es usar el script run.sh que automatiza todo el proceso:

📋 Ver comandos disponibles:
    ./run.sh help

🚀 Iniciar la aplicación (construye Docker si es necesario):
    ./run.sh start

🧪 Probar la función con payload.json:
    ./run.sh test

📊 Ver estado del contenedor:
    ./run.sh status

📋 Ver logs en tiempo real:
    ./run.sh logs

🛑 Detener la aplicación:
    ./run.sh stop

🧹 Limpiar contenedor:
    ./run.sh clean

--- Comandos manuales (si no usas run.sh) ---

Construir imagen Docker:
    docker build -t reading-pdf-paragraphs .

Ejecutar contenedor:
    docker run -d --name reading-pdf-paragraphs-container -p 9000:8080 reading-pdf-paragraphs

Probar función Lambda:
    curl -X POST "http://localhost:9000/2015-03-31/functions/function/invocations" \
         -H "Content-Type: application/json" \
         --data-binary @payload.json

========================
Build y deploy (Docker + ECR + Lambda)
========================

El script deploy.sh hace build, push a ECR y update de la Lambda:

    sh deploy.sh

Cambiar etiqueta (tag):

    TAG=lambda-v2 sh deploy.sh

========================
Emular Lambda localmente (Docker runtime de AWS)
========================

    1. Levantar el runtime con tu imagen:

    docker run --rm -p 9000:8080 pdf-paragraphs:lambda-v1


    2. Crear un evento HTTP API v2 con tu payload:

    printf '{ "requestContext": {"http": {"method":"POST"}}, "isBase64Encoded": false, "body": %s }\n' \
    "$(jq -c . payload.json)" > event-local.json


    3. Invocar localmente:

    curl -s -XPOST "http://localhost:9000/2015-03-31/functions/function/invocations" \
    -H "Content-Type: application/json" \
    --data-binary @event-local.json | python3 -m json.tool

========================
Invocar la Lambda real (AWS CLI)
========================


Reutiliza event-local.json (envelope HTTP API v2):

aws lambda invoke \
  --function-name "$FUNCTION_NAME" \
  --payload fileb://event-local.json \
  --cli-binary-format raw-in-base64-out \
  response.json

cat response.json | python3 -m json.tool

Invocar por API Gateway

Endpoint:
POST $API_ENDPOINT/prod/extract_paragraphs

Body: el contenido de payload.json (tiene pdf_base64 y pages).

curl -s -X POST "$API_ENDPOINT/prod/extract_paragraphs" \
  -H "Content-Type: application/json" \
  --data-binary @payload.json | python3 -m json.tool

Postman

Method: POST

URL: https://<API_ID>.execute-api.<REGION>.amazonaws.com/prod/extract_paragraphs

Headers: Content-Type: application/json

Body: raw → JSON → pega payload.json.

Logs en CloudWatch

Tail en vivo:

aws logs tail /aws/lambda/$FUNCTION_NAME --follow --region "$AWS_REGION"


Último log stream:

aws logs describe-log-streams \
  --log-group-name /aws/lambda/$FUNCTION_NAME \
  --order-by LastEventTime \
  --descending \
  --limit 1 --region "$AWS_REGION"


Ver eventos de un stream:

    aws logs get-log-events \
      --log-group-name /aws/lambda/$FUNCTION_NAME \
      --log-stream-name <STREAM_NAME> --region "$AWS_REGION"

========================
🧪 TESTING Y DEBUGGING
========================

📝 Generar tu propio payload:

Si quieres usar tu propio PDF en lugar de sample.pdf:

    # 1. Convertir PDF a base64
    base64 -i tu_archivo.pdf > pdf.b64

    # 2. Crear payload.json
    jq -n --arg pdf "$(cat pdf.b64)" --arg pages "1-5" \
    '{pdf_base64:$pdf, pages:$pages}' > payload.json

    # 3. Probar
    ./run.sh test

🔍 Ver logs en tiempo real:

    ./run.sh logs

📊 Verificar estado:

    ./run.sh status

🧹 Limpiar y reiniciar:

    ./run.sh clean
    ./run.sh start

========================
🔧 TROUBLESHOOTING
========================

❌ Error "Cannot connect to the Docker daemon"
   Solución: Iniciar Docker Desktop

❌ Error "Port 9000 already in use"
   Solución: ./run.sh clean && ./run.sh start

❌ Error durante docker build
   Solución: Verificar conexión a internet y reintentar

❌ El test devuelve error 500
   - Verificar que payload.json es válido: jq . payload.json
   - Verificar logs: ./run.sh logs
   - Reiniciar: ./run.sh restart

❌ PyMuPDF no se instala localmente
   Solución: Usar Docker (recomendado): ./run.sh start

📚 Para más ayuda:
   - Ver logs: ./run.sh logs  
   - Verificar el Dockerfile
   - Revisar requirements.txt

========================
📋 COMANDOS RÁPIDOS
========================

    # Inicio rápido
    ./run.sh start && ./run.sh test

    # Ver todo funcionando
    ./run.sh status && ./run.sh logs

    # Reinicio completo
    ./run.sh clean && ./run.sh start

    # Ayuda
    ./run.sh help

aws logs get-log-events \
  --log-group-name /aws/lambda/$FUNCTION_NAME \
  --log-stream-name '<LOG_STREAM_NAME>' \
  --region "$AWS_REGION"