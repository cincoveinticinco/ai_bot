# esta copia ejecuta open ai directo con prmpt y pregunta
import json
import os
import time
from dotenv import load_dotenv
from openai import OpenAI

# Cargar variables desde .env
load_dotenv()

def lambda_handler(event, context):
    # question = event.get("question")
    if "body" in event:
        # Viene de API Gateway
        body = json.loads(event.get("body", "{}"))
    else:
        # Viene de llamada directa (CLI o Ruby)
        body = event

    question = set_question(body)
    print(f"Pregunta procesada: {question}")
    prompt_type = str(body.get("type", "1"))  # default a "1" si no viene
    model_to_use = "gpt-4-turbo" if prompt_type == "2" else "gpt-3.5-turbo" # default a "gpt-4-turbo" si no viene
    model_to_use = body.get("model", model_to_use)  
    print(f"Pregunta recibida: {question}")
    print(f"Tipo de prompt: {prompt_type}")
    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps("Missing 'question' in event")
        }
    prompt_template = load_prompt(prompt_type)
    # lest measure how long it takes to receive the response, first print time stamp befrore the request and then after the request
    
    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        chat_completion = client.chat.completions.create(
            model=model_to_use,
            messages=[
                {"role": "system", "content": prompt_template},
                {"role": "user", "content": question}
            ],
            temperature=0
        )
        ai_response = chat_completion.choices[0].message.content
        if prompt_type == "2":
            return {
            "statusCode": 200,
            "body": json.dumps({"answer": ai_response})  # empaquetamos el string en JSON
        }
        else:
            return {
                "statusCode": 200,
                "body": ai_response
            }

    except Exception as e:
        print(f"end: {time.time()}")
        return {
            "statusCode": 500,
            "body": json.dumps(str(e))
        }

def load_prompt(prompt_type, language="es"):
    if prompt_type == "2":
        filename = f"summary_analysis_{language}.txt"
    elif prompt_type == "3":
        filename = f"other_analysis_{language}.txt"
    else:
        filename = f"first_analysis_{language}.txt"

    path = os.path.join("prompts", filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def set_question(body):
    question = body.get("question")
    type = body.get("type", "1")
    if type == "1":
        return question
    elif type == "2":
        data_set = body.get("data_set", {})
        scenes_data = body.get("scenes_data", [])
        return f"""
Pregunta:
{question}

Escenas:
{json.dumps(scenes_data, ensure_ascii=False)}

llaves de ids:
{json.dumps(data_set, ensure_ascii=False)}

"""
    else:
        return question


if __name__ == "__main__":
    with open("events/event.json") as f:
        event = json.load(f)
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
