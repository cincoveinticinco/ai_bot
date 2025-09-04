import os
from dotenv import load_dotenv
import openai

# Cargar .env
load_dotenv()

# Leer la API key
api_key = os.getenv("OPENAI_API_KEY")

# Verificar y mostrar el resultado
if api_key:
    print("✅ OPENAI_API_KEY cargada correctamente.")
    print(f"🔑 API Key (oculta parcialmente): {api_key[:10]}...{api_key[-5:]}")
else:
    print("❌ No se pudo cargar OPENAI_API_KEY. Revisa el archivo .env")

# Crear el cliente de OpenAI
client = openai.OpenAI(api_key=api_key)

try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": "Hola, ¿puedes decirme un dato curioso?"}
        ],
        temperature=0.5,
    )

    print("✅ Respuesta de OpenAI:")
    print(response.choices[0].message.content)

except Exception as e:
    print("❌ Error al conectarse con OpenAI:")
    print(str(e))
