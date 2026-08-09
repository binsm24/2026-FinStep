from typing import Any
import re

NEGATION_PATTERNS = [
    r"하지\s*않",
    r"안\s+(?:보내|송금|입금|이체|계약|투자|제공)",
    r"않고",
    r"않겠습니다",
    r"않는다",
    r"말아야",
    r"못\s+(?:보내|송금|입금|이체)",
]


def is_negated(answer: str, keyword: str) -> bool:
    """
    키워드가 부정 표현의 대상인지 확인합니다.

    예:
    - 송금하지 않는다 → True
    - 송금하고 확인한다 → False
    """
    keyword_index = answer.find(keyword)

    if keyword_index == -1:
        return False

    # 키워드 앞뒤 12글자 정도만 확인해 부정 표현을 판단합니다.
    start = max(0, keyword_index - 12)
    end = min(len(answer), keyword_index + len(keyword) + 12)
    context = answer[start:end]

    return any(
        re.search(pattern, context)
        for pattern in NEGATION_PATTERNS
    )

SCENARIO_RULES: dict[str, list[dict[str, Any]]] = {
    "jeonse-fraud": [
        {
            "keywords": ["계약금", "송금", "입금", "보낸다", "계약한다"],
            "score": -35,
            "action": "확인 전 계약 또는 송금",
            "feedback": "확인 전에 계약이나 금전 거래를 진행하려는 행동이 발견되었습니다.",
        },
        {
            "keywords": ["서두", "오늘", "빨리", "즉시"],
            "score": -20,
            "action": "계약을 서두름",
            "feedback": "시간 압박에 따라 바로 결정하려는 행동은 위험할 수 있습니다.",
        },
        {
            "keywords": ["등기부등본", "등기부"],
            "score": 25,
            "action": "등기부등본 확인",
            "feedback": "계약 전 권리관계를 확인하려는 점이 좋습니다.",
        },
        {
            "keywords": ["시세", "주변 가격", "주변 시세"],
            "score": 20,
            "action": "주변 시세 확인",
            "feedback": "주변 시세를 비교하려는 점이 좋습니다.",
        },
        {
            "keywords": ["보류", "기다", "하지 않", "계약하지"],
            "score": 20,
            "action": "계약 보류",
            "feedback": "확인이 끝날 때까지 결정을 보류하려는 점이 좋습니다.",
        },
        {
            "keywords": ["집주인", "소유자", "소유권"],
            "score": 20,
            "action": "임대인 정보 확인",
            "feedback": "계약 상대방의 정보를 확인하려는 점이 좋습니다.",
        },
    ],
    "voice-phishing": [
        {
            "keywords": ["송금", "입금", "이체", "보낸다", "안전계좌"],
            "score": -45,
            "action": "상대방이 안내한 계좌로 송금",
            "feedback": "수사기관을 사칭한 상대방의 계좌로 송금하는 것은 매우 위험합니다.",
        },
        {
            "keywords": ["개인정보", "인증번호", "비밀번호", "주민번호"],
            "score": -40,
            "action": "개인정보 제공",
            "feedback": "전화로 개인정보나 인증번호를 제공하면 안 됩니다.",
        },
        {
            "keywords": ["끊", "전화 종료"],
            "score": 25,
            "action": "전화 종료",
            "feedback": "상대방의 통화를 종료하려는 점이 좋습니다.",
        },
        {
            "keywords": ["공식", "대표번호", "직접 확인", "기관에 확인"],
            "score": 35,
            "action": "공식 기관에 직접 확인",
            "feedback": "상대방이 알려준 경로가 아닌 공식 경로로 확인하려는 점이 좋습니다.",
        },
        {
            "keywords": ["가족", "지인", "친구", "상담"],
            "score": 20,
            "action": "주변에 도움 요청",
            "feedback": "혼자 판단하지 않고 주변에 알리려는 점이 좋습니다.",
        },
        {
            "keywords": ["의심", "믿지 않", "사기"],
            "score": 20,
            "action": "상황을 의심",
            "feedback": "상대방의 요구를 의심한 점이 좋습니다.",
        },
    ],
    "investment-fraud": [
        {
            "keywords": ["투자한다", "투자해", "송금", "입금", "이체"],
            "score": -40,
            "action": "투자금 송금",
            "feedback": "검증되지 않은 투자 제안에 돈을 보내는 것은 위험합니다.",
        },
        {
            "keywords": ["소액", "조금만"],
            "score": -20,
            "action": "소액 투자 시도",
            "feedback": "소액이라도 검증되지 않은 상품에 투자하면 안 됩니다.",
        },
        {
            "keywords": ["의심", "수익률이 높", "너무 높", "원금 보장"],
            "score": 25,
            "action": "고수익 보장 문구 의심",
            "feedback": "비현실적인 수익률과 원금 보장 문구를 의심한 점이 좋습니다.",
        },
        {
            "keywords": ["등록 여부", "금융회사", "공식", "금융감독원"],
            "score": 30,
            "action": "공식 정보 확인",
            "feedback": "공식 기관과 금융회사 정보를 확인하려는 점이 좋습니다.",
        },
        {
            "keywords": ["보류", "하지 않", "투자하지", "기다"],
            "score": 25,
            "action": "투자 보류",
            "feedback": "충분히 확인할 때까지 투자를 보류하려는 점이 좋습니다.",
        },
    ],
}

def get_risk_level(score: int) -> tuple[str, str]:
    if score >= 31:
        return "low", "안전한 대응"
    if score >= -30:
        return "medium", "주의가 필요한 대응"
    return "high", "위험한 대응"


def analyze_answer(scenario_id: str, answer: str) -> dict[str, Any]:
    rules = SCENARIO_RULES.get(scenario_id)

    if rules is None:
        raise ValueError("존재하지 않는 시나리오입니다.")

    score = 0
    detected_actions: list[str] = []
    safe_actions: list[str] = []
    feedbacks: list[str] = []

    for rule in rules:
        matched_keyword = next(
            (
                keyword
                for keyword in rule["keywords"]
                if keyword in answer
            ),
            None,
        )

        if matched_keyword is None:
            continue

        if rule["score"] < 0 and is_negated(answer, matched_keyword):
            continue

        score += rule["score"]

        if rule["score"] < 0:
            detected_actions.append(rule["action"])
        else:
            safe_actions.append(rule["action"])

        feedbacks.append(rule["feedback"])

    risk_level, risk_label = get_risk_level(score)

    if not detected_actions:
        feedback = (
            "답변에서 명확한 행동이 충분히 확인되지 않았습니다. "
            "금전 거래를 중단하고 공식 기관에 확인하는 것이 안전합니다."
        )
    elif risk_level == "high":
        feedback = (
            "현재 답변에는 금융 위험에 노출될 수 있는 행동이 포함되어 있습니다. "
            + feedbacks[0]
        )
    elif risk_level == "medium":
        feedback = (
            "일부 안전한 행동이 있지만 추가적인 확인이 필요합니다. "
            + feedbacks[0]
        )
    else:
        feedback = (
            "금융 위험을 줄이기 위한 대응을 하고 있습니다. "
            + feedbacks[-1]
        )

    return {
        "score": score,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "detected_actions": detected_actions,
        "safe_actions": safe_actions,
        "feedback": feedback,
    }
