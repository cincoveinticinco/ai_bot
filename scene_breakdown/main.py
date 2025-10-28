# Ejecuta OpenAI con prompt + question; adjunta instrucciones + schema como texto

from dotenv import load_dotenv
from openai import OpenAI
import openai, sys, json, time, os, re

# Debug de versión en runtime
print("openai version:", openai.__version__, "python:", sys.version)

# Cargar variables desde .env
load_dotenv()

# MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-4o-mini")
MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-4.1")
# MODEL_DEFAULT = os.getenv("MODEL_TO_USE", "gpt-5")
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
    for scene in scenes:
        print("scene here")
        scene_obj = get_completion(scene, prompt_template, model=model_to_use)
        break_scenes.append(scene_obj)

    
    end_time = time.time()
    elapsed_time = end_time - start_time
    # save break_scenes as json file
    # with open(f"responses/break_scenes_{model_to_use}.json", "w", encoding="utf-8") as f:
    #     json.dump(break_scenes, f, ensure_ascii=False, indent=2)
    print(f"Tiempo total para procesar {len(scenes)} escenas: {elapsed_time} segundos")

    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json; charset=utf-8"},
        "body": json.dumps({"scenes": break_scenes}, ensure_ascii=False)
    }
def _extract_json(text: str):
    # fallback por si algún modelo llega a poner fences (no debería con JSON mode)
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.I)
    if m:
        text = m.group(1)
    return _extract_json(text)

def get_completion(scene, prompt: str, model: str = MODEL_DEFAULT, max_retries: int = 3):
    """
    Llama a OpenAI con reintentos y fuerza salida JSON usando Chat Completions.
    """
    

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
            resp = client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question}
                ],
            )
            print("=== Respuesta completa ===")
            print(resp)
            if len(resp.output) > 1 and hasattr(resp.output[1], "content"):
                txt = resp.output[1].content[0].text.strip()
            else:
                txt = resp.output[0].content[0].text.strip()

            print("=== Texto devuelto ===")
            print(txt)
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
