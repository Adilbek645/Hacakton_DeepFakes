import os
import json
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

generation_config = {
    "temperature": 0.2,
    "response_mime_type": "application/json",
}

batch_model = genai.GenerativeModel(
    model_name="gemini-flash-latest",
    generation_config=generation_config
)

texts = [
    "Это отличный день для программирования!",
    "ШОК! Врачи скрывают правду о воде!"
]

prompt = "У меня есть список текстов. Оцени каждый текст на признаки кликбейта.\n\nТексты:\n"
for i, text in enumerate(texts):
    prompt += f"[{i}]: {text}\n\n"
prompt += "Отвечай СТРОГО в формате JSON массива (list of objects), где каждый объект имеет ключи: is_fake (boolean), trust_score (integer 0-100, 100=полностью безопасно) и explanation (краткая строка)."

response = batch_model.generate_content(prompt)
print("--- RAW RESPONSE ---")
print(response.text)
print("--- END RAW RESPONSE ---")
