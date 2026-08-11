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

def generate_next_response(
    scenario_title: str,
    current_stage_title: str,
    current_message: str,
    user_answer: str,
    next_stage_title: str,
    next_stage_description: str,
    next_stage_message: str,
) -> dict[str, Any]:
    """
    현재 단계의 사용자 답변을 반영해 다음 단계의 상대방 메시지를 생성합니다.
    Gemini 실패 시 고정 메시지를 fallback으로 반환합니다.
    """

    fallback_message = next_stage_message

    if client is None or not model:
        return {
            "message": fallback_message,
            "llm_available": False,
        }

    prompt = f"""
너는 금융 위험 대응 시뮬레이터에 등장하는 상대방 역할이다.

사용자는 금융 위험 상황에 대응하고 있다.
다음 단계의 위험 신호를 유지하면서, 사용자의 답변에 자연스럽게 반응하는
상대방의 메시지를 생성해라.

반드시 JSON 객체만 반환해라.
마크다운, 해설, 분석 문장은 포함하지 마라.

반환 형식:
{{
  "message": "상대방이 말하는 1~3개의 짧은 문장"
}}

규칙:
1. 상대방의 말만 생성한다.
2. 1~3문장으로 작성한다.
3. 현재 시나리오의 역할과 말투를 유지한다.
4. 다음 단계의 핵심 위험 신호를 반드시 포함한다.
5. 사용자의 답변이 안전해도 상대방은 계속 설득하거나 압박할 수 있다.
6. 사용자의 답변이 위험해도 과도하게 즉시 결말을 내지 않는다.
7. 새로운 계좌번호, 전화번호, URL, 개인정보를 만들어내지 않는다.
8. 실제 금융 거래를 유도하는 조언처럼 작성하지 않는다.
9. 교육용 시뮬레이션이라는 맥락을 벗어나지 않는다.

시나리오: {scenario_title}
현재 단계: {current_stage_title}
현재 상대방 메시지: {current_message}
사용자 답변: {user_answer}

다음 단계: {next_stage_title}
다음 단계 설명: {next_stage_description}
반드시 유지할 다음 단계의 기본 메시지:
{next_stage_message}
"""

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
            ),
        )

        parsed = json.loads(response.text or "{}")
        generated_message = parsed.get("message")

        if not isinstance(generated_message, str):
            raise ValueError("Gemini 응답에 message가 없습니다.")

        generated_message = generated_message.strip()

        if not generated_message:
            raise ValueError("Gemini 응답 message가 비어 있습니다.")

        return {
            "message": generated_message,
            "llm_available": True,
        }

    except Exception as error:
        print(f"Gemini response generation failed: {error}")

        return {
            "message": fallback_message,
            "llm_available": False,
        }
