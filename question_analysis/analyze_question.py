# --- desactivar rutas que disparan FastAPI / proxy ---
import os
os.environ.setdefault("LITELLM_LOG", "ERROR")   # en vez de "False"
os.environ.setdefault("LITELLM_CACHE", "False") # este sí puede ser "False"
os.environ.setdefault("DSPY_LOGGING", "False")
# -----------------------------------------------------

import json
import sys
# (importa el resto recién ahora)
import dspy
from dotenv import load_dotenv  # si lo usas localmente
import openai
# Debug de versión en runtime
print("openai version:", openai.__version__, "python:", sys.version)

# Cargar variables desde .env
load_dotenv()

MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-4o-mini")
LANG_DEFAULT = os.getenv("PROMPT_LANG", "es")
API_KEY = os.getenv("OPENAI_API_KEY")
with open(os.path.join("prompts", "schemas", "trainset.json"), "r", encoding="utf-8") as f:
    trainset_data = json.load(f)

# Configure DSPy with the new API (v3.0+)
lm = dspy.LM(f"openai/{MODEL_DEFAULT}", api_key=API_KEY)
dspy.settings.configure(lm=lm)

# Convert trainset to DSPy v3.0+ format
TRAINSET = []
for item in trainset_data:
    example = dspy.Example(
        question=item["question"],
        json_output=json.dumps(item["json_object"], ensure_ascii=False)
    ).with_inputs("question")
    TRAINSET.append(example)

class AgentSignature(dspy.Signature):
    question = dspy.InputField(desc="Question in natural language about the project.")
    json_output = dspy.OutputField(desc="A valid JSON object with the analysis structure.")

class AgentDSPy(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predictor = dspy.Predict(AgentSignature)

    def forward(self, question):
        return self.predictor(question=question)
# 3. Compilar el programa optimizado
agent_program = AgentDSPy()
teleprompter = dspy.teleprompt.BootstrapFewShot(metric=None)
agent_optimized = teleprompter.compile(agent_program, trainset=TRAINSET)


def lambda_handler(event, context):
    # Compatibilidad API Gateway / llamada directa
    body = json.loads(event.get("body", "{}")) if "body" in event else event

    question = body.get("question")
    prompt_type = str(body.get("type", "1"))  # "1" por defecto

    if not question:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps("Missing 'question' in event")
        }

    try:
        response = agent_optimized(question=question)
        text = response.json_output
       
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

if __name__ == "__main__":
    with open("events/event.json") as f:
        event = json.load(f)
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
