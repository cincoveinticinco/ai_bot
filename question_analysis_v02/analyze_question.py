# Ejecuta OpenAI con prompt + question; adjunta instrucciones + schema como texto
import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI
import openai, sys

# Debug de versión en runtime
print("openai version:", openai.__version__, "python:", sys.version)

# Cargar variables desde .env
load_dotenv()

MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-4o-mini")
LANG_DEFAULT = os.getenv("PROMPT_LANG", "es")

def lambda_handler(event, context):
    # Compatibilidad API Gateway / llamada directa
    body = json.loads(event.get("body", "{}")) if "body" in event else event

    question = body.get("question")
    prompt_type = str(body.get("type", "1"))  # "1" por defecto
    model_to_use = body.get("model", MODEL_DEFAULT)
    language = body.get("lang", LANG_DEFAULT)

    if not question:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps("Missing 'question' in event")
        }

    # Prompt base + (opcional) instrucciones de salida con schema
    prompt_template = load_prompt(prompt_type, language=language)
    schema_instructions = load_json_schema(prompt_type)
    if schema_instructions:
        prompt_template = f"{prompt_template}\n\n{schema_instructions}"

    print(f"Pregunta recibida: {question}")
    print(f"Tipo de prompt: {prompt_type}")
    print(f"Modelo a usar: {model_to_use}")
    print(f"Tiene schema: {bool(schema_instructions)}")

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.responses.create(
            model=model_to_use,
            instructions=prompt_template,
            input=[{"role": "user", "content": question}],
            temperature=0
        )
        text = getattr(resp, "output_text", "")

        # Si quieres que type==2 siempre responda {answer: ...}, mantenemos esto:
        if prompt_type == "2":
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": json.dumps({"answer": text}, ensure_ascii=False)
            }
        else:
            return {
                "statusCode": 200,
                "headers": {"Content-Type": "application/json; charset=utf-8"},
                "body": text
            }

    except Exception as e:
        print("Exception:", repr(e))
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps(str(e), ensure_ascii=False)
        }


def load_prompt(prompt_type: str, language: str = "es") -> str:
    """
    Carga el prompt base desde /prompts según el tipo.
    type=1 -> entities_prompt.txt
    type=2 -> summary_analysis_<lang>.txt
    type=3 -> other_analysis_<lang>.txt
    """
    if prompt_type == "2":
        filename = f"summary_analysis_{language}.txt"
    elif prompt_type == "3":
        filename = f"other_analysis_{language}.txt"
    else:
        filename = "entities_prompt.txt"

    path = os.path.join("prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().rstrip()


def load_json_schema(prompt_type: str) -> str | None:
    """
    Lee el schema JSON desde prompts/schemas/<archivo>.json,
    lo serializa bonito y devuelve el bloque de 'Instrucciones de salida'
    listo para pegar al prompt. Si no hay schema para el tipo, devuelve None.
    """
    print("**" * 60)
    print("**" * 60)
    print(f"Loading JSON schema for prompt type: {prompt_type}")

    SCHEMAS_DIR = os.path.join("prompts", "schemas")
    mapping = {
        "1": "entities_schema.json",
        # "2": "summary_schema.json",
        # "3": "other_schema.json",
    }
    filename = mapping.get(prompt_type)
    print(f"Schema filename: {filename}")
    if not filename:
        return None

    path = os.path.join(SCHEMAS_DIR, filename)
    print(f"Schema path: {path}")
    print(os.path.exists(path))
    if not os.path.exists(path):
        print(f"Schema file not found: {path}")
        return None

    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    # Convertir el dict a JSON string con formato legible
    schema_text = json.dumps(schema, ensure_ascii=False, indent=2)

    # Bloque de instrucciones
    instructions = (
        "📌 Instrucciones de salida (MUY IMPORTANTE):\n"
        "1) Devuelve **solo un JSON válido** que sea **una instancia** que cumpla el esquema.\n"
        "2) **NO** devuelvas el esquema. **NO** incluyas claves como \"$schema\", \"title\", \"$defs\", \"properties\".\n"
        "3) **NO** agregues texto fuera del JSON.\n"
        "4) Usa únicamente las claves permitidas por el esquema.\n\n"
        "### Referencia del esquema (NO COPIAR, SOLO REFERENCIA)\n"
        f"{schema_text}\n\n"
        "### Ejemplo de salida (solo ilustrativo, AJUSTA a la pregunta):\n"
        "{\n"
        "  \"entities\": [\n"
        "    {\n"
        "      \"type\": \"ie\",\n"
        "      \"metrics\": [\n"
        "        { \"name\": \"count_scn\", \"filters\": [] },\n"
        "        { \"name\": \"pct_project_count_scn\", \"filters\": [] }\n"
        "      ],\n"
        "      \"children\": [],\n"
        "      \"filters\": [\n"
        "        { \"field\": \"ie\", \"op\": \"eq\", \"values\": [\"ext\"], \"negate\": false }\n"
        "      ]\n"
        "    }\n"
        "  ],\n"
        "  \"clarifications\": []\n"
        "}\n\n"
        "---\n"
        "Repite: **NO devuelvas el esquema**, devuelve **una instancia**.\n"
        "No escribas texto fuera del JSON.\n"
    )

    return instructions


if __name__ == "__main__":
    with open("events/event.json") as f:
        event = json.load(f)
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
