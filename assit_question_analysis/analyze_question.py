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

    question = body.get("question")
    print(f"Pregunta procesada: {question}")
    if not question:
        return {
            "statusCode": 400,
            "body": json.dumps("Missing 'question' in event")
        }
    # Let's measure how long it takes to receive the response, first print time stamp before the request and then after the request

    try:
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        ASSISTANT_ID = os.getenv("ASSISTANT_ID")  # guardado en tu .env o Lambda env

        # 1. Create a new thread
        thread = client.beta.threads.create()
        # 2. Add the user's question
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        # 3. Execute the run of the already created assistant
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID
        )
         # 4. wait for the run to complete
        while True:
            run_status = client.beta.threads.runs.retrieve(
                thread_id=thread.id,
                run_id=run.id
            )
            if run_status.status in ["completed", "failed"]:
                break
            time.sleep(1)
        # 5. Obtener la respuesta
        messages = client.beta.threads.messages.list(thread_id=thread.id)

        ai_response = None
        for msg in messages.data:
            if msg.role == "assistant":
                ai_response = msg.content[0].text.value
                break
        
        return {
            "statusCode": 200,
            "body": ai_response or "No hubo respuesta"
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps(str(e))
        }
    # except Exception as e:
    #     return {
    #         "statusCode": 500,
    #         "body": f"Error: {str(e)}"
    #     }

if __name__ == "__main__":
    with open("events/event.json") as f:
        event = json.load(f)
    response = lambda_handler(event, None)
    print(json.dumps(response, indent=2, ensure_ascii=False))
