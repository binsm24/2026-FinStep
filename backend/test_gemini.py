import os

from dotenv import load_dotenv
from google import genai


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY가 설정되지 않았습니다. backend/.env를 확인하세요."
    )

client = genai.Client(api_key=api_key)

response = client.models.generate_content(
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    contents="FinStep 금융 위험 시뮬레이터를 한 문장으로 설명해줘.",
)

print(response.text)
