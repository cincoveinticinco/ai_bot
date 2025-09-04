# Ejecuta OpenAI con prompt + question; adjunta instrucciones + schema como texto
import json
import os
import re
import time
from dotenv import load_dotenv
from openai import OpenAI
import openai, sys

# Debug de versión en runtime
print("openai version:", openai.__version__, "python:", sys.version)

# Cargar variables desde .env
load_dotenv()

MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-4o-mini")
# MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-4.1")
LANG_DEFAULT = os.getenv("PROMPT_LANG", "es")

def lambda_handler(event, context):
    # Compatibilidad API Gateway / llamada directa
    body = json.loads(event.get("body", "{}")) if "body" in event else event

    scenes = body.get("scenes")
    model_to_use = body.get("model", MODEL_DEFAULT)
    language = body.get("lang", LANG_DEFAULT)

    if not scenes:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json; charset=utf-8"},
            "body": json.dumps("Missing 'scenes' in event")
        }

    # Prompt base + (opcional) instrucciones de salida con schema
    prompt_template = load_prompt(language=language)

    print(f"Modelo a usar: {model_to_use}")
    start_time = time.time()
    break_scenes = []
    for scene in scenes[12:15]:
        print("scene here")
        scene_obj = get_completion(scene, prompt_template, model=model_to_use)
        break_scenes.append(scene_obj)

    
    end_time = time.time()
    elapsed_time = end_time - start_time
    # save break_scenes as json file
    with open("break_scenes_4o-mini.json", "w", encoding="utf-8") as f:
        json.dump(break_scenes, f, ensure_ascii=False, indent=2)
    print(f"Tiempo total para procesar {len(scenes)} escenas: {elapsed_time} segundos")
def _extract_json(text: str):
    # fallback por si algún modelo llega a poner fences (no debería con JSON mode)
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.I)
    if m:
        text = m.group(1)
    return _extract_json(text)

def get_completion(scene, prompt: str, model: str = MODEL_DEFAULT, max_retries: int = 5):
    """
    Llama a OpenAI con reintentos y fuerza salida JSON usando Chat Completions.
    """
    from openai import OpenAI
    import json, time, os, re

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    def _extract_json(text: str):
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.I)
        if m:
            text = m.group(1)
        return json.loads(text)

    # Prepara la escena (solo text/type)
    scene_paras = [{"type": p.get("type"), "text": p.get("text")} for p in scene.get("content", [])]
    paras_json = json.dumps(scene_paras, ensure_ascii=False, indent=2)
    question = f"Escena:\n{paras_json}\n\nDevuelve el JSON solicitado."

    for attempt in range(max_retries):
        try:
            resp = client.chat.completions.create(
                model=model,
                response_format={"type": "json_object"},  # JSON mode
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question}
                ],
                temperature=0,
                max_tokens=600
            )
            txt = resp.choices[0].message.content.strip()
            return _extract_json(txt)  # dict
        except Exception as e:
            wait_time = 2 ** attempt
            print(f"Error en intento {attempt + 1}/{max_retries}: {e}. Reintentando en {wait_time} segundos...")
            time.sleep(wait_time)
    raise Exception(f"Fallo después de {max_retries} intentos.")



def load_prompt(language: str = "es") -> str:
    """
    Carga el prompt base desde /prompts según el lenguaje.
    """
    filename = f"breakdown_prompt_{language}.txt"

    path = os.path.join("prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read().rstrip()



if __name__ == "__main__":
    with open("events/event.json") as f:
        event = json.load(f)
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
