import json
import os
from typing import Any

from dotenv import load_dotenv
from google import genai
from google.genai import types


load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL")

client = genai.Client(api_key=api_key) if api_key else None


ALLOWED_ACTION_TYPES = {
    "transfer_money",
    "provide_personal_info",
    "continue_communication",
    "official_verification",
    "consult_others",
    "stop_or_delay",
    "check_documents",
    "invest_money",
    "question_pressure",
}


def analyze_answer_with_llm(
    scenario_title: str,
    stage_title: str,
    situation: str,
    answer: str,
) -> dict[str, Any]:
    """
    사용자 답변의 행동 의도를 Gemini로 분석합니다.
    Gemini 호출 실패 시 fallback 결과를 반환합니다.
    """

    if client is None or not model:
        return {
            "actions": [],
            "risk_signals": [],
            "llm_available": False,
            "message": "Gemini 환경 변수가 설정되지 않았습니다.",
        }

    prompt = f"""
너는 금융 위험 대응 시뮬레이터의 행동 분석기다.

사용자 답변에서 실제 행동 의도를 분류해라.
반드시 JSON 객체만 반환하고 마크다운은 사용하지 마라.

허용된 행동 타입:
- transfer_money: 송금, 입금, 이체하려는 행동
- provide_personal_info: 개인정보, 인증번호, 계좌정보 제공
- continue_communication: 의심하면서도 통화나 대화를 계속함
- official_verification: 공식 기관이나 대표번호로 직접 확인
- consult_others: 가족, 지인, 전문가에게 상담
- stop_or_delay: 중단, 거절, 보류
- check_documents: 등기부등본, 계약서, 상품 정보 확인
- invest_money: 투자하려는 행동
- question_pressure: 시간 압박, 고수익, 비정상 요구를 의심

중요:
- "송금하지 않는다"는 transfer_money가 아니다.
- "개인정보를 제공하지 않는다"는 provide_personal_info가 아니다.
- "계약하지 않고 확인한다"는 위험 행동이 아니다.

반환 형식:
{{
  "actions": [
    {{
      "type": "official_verification",
      "confidence": 0.95
    }}
  ],
  "risk_signals": [
    "공식 기관에 확인하려는 행동"
  ]
}}

시나리오: {scenario_title}
현재 단계: {stage_title}
상황: {situation}
사용자 답변: {answer}
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )

        parsed = json.loads(response.text or "{}")

        actions = [
            action
            for action in parsed.get("actions", [])
            if isinstance(action, dict)
            and action.get("type") in ALLOWED_ACTION_TYPES
        ]

        return {
            "actions": actions,
            "risk_signals": parsed.get("risk_signals", []),
            "llm_available": True,
        }

    except Exception as error:
        print(f"Gemini analysis failed: {error}")

        return {
            "actions": [],
            "risk_signals": [],
            "llm_available": False,
            "message": "Gemini 분석 실패로 규칙 기반 분석을 사용합니다.",
        }
