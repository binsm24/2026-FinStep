from typing import Any
from uuid import uuid4

from data.scenarios import MULTI_STAGE_SCENARIOS
from services.llm_service import analyze_answer_with_llm

simulation_sessions: dict[str, dict[str, Any]] = {}


def find_scenario(scenario_id: str) -> dict[str, Any] | None:
    return next(
        (
            scenario
            for scenario in MULTI_STAGE_SCENARIOS
            if scenario["id"] == scenario_id
        ),
        None,
    )


def create_session(scenario_id: str) -> dict[str, Any]:
    scenario = find_scenario(scenario_id)

    if scenario is None:
        raise ValueError("존재하지 않는 시나리오입니다.")

    session_id = str(uuid4())

    simulation_sessions[session_id] = {
        "session_id": session_id,
        "scenario_id": scenario_id,
        "current_stage": 1,
        "total_score": 0,
        "stage_results": [],
        "is_finished": False,
    }

    stage = scenario["stages"][0]

    return {
        "session_id": session_id,
        "scenario_id": scenario_id,
        "scenario_title": scenario["title"],
        "stage": stage["stage"],
        "stage_title": stage["title"],
        "description": stage["description"],
        "messages": stage["messages"],
        "total_stages": scenario["total_stages"],
        "is_finished": False,
    }


def is_negated(answer: str, keyword: str) -> bool:
    keyword_index = answer.find(keyword)

    if keyword_index == -1:
        return False

    context_start = max(0, keyword_index - 12)
    context_end = min(
        len(answer),
        keyword_index + len(keyword) + 12,
    )
    context = answer[context_start:context_end]

    negations = [
        "하지 않",
        "안 ",
        "않고",
        "않는다",
        "않겠습니다",
        "말지",
        "말아",
    ]

    return any(negation in context for negation in negations)

LLM_ACTION_SCORES = {
    "transfer_money": -50,
    "provide_personal_info": -40,
    "continue_communication": -15,
    "official_verification": 35,
    "consult_others": 25,
    "stop_or_delay": 30,
    "check_documents": 30,
    "invest_money": -45,
    "question_pressure": 25,
}

LLM_ACTION_LABELS = {
    "transfer_money": "송금·입금·이체 의도",
    "provide_personal_info": "개인정보 제공 의도",
    "continue_communication": "대화 또는 통화 지속",
    "official_verification": "공식 기관 확인",
    "consult_others": "가족·지인·전문가 상담",
    "stop_or_delay": "중단·거절·보류",
    "check_documents": "관련 문서·정보 확인",
    "invest_money": "투자 의사",
    "question_pressure": "압박 또는 비정상 조건 의심",
}

def analyze_stage_answer(
    answer: str,
    stage: dict[str, Any],
) -> dict[str, Any]:
    score = 0
    safe_actions: list[str] = []
    risky_actions: list[str] = []

    for rule in stage["rules"]:
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

        if rule["type"] == "risky" and is_negated(
            answer,
            matched_keyword,
        ):
            continue

        score += rule["score"]

        if rule["type"] == "safe":
            safe_actions.append(rule["action"])
        else:
            risky_actions.append(rule["action"])

    return {
        "score": score,
        "safe_actions": safe_actions,
        "risky_actions": risky_actions,
    }


def submit_stage_answer(
    session_id: str,
    answer: str,
) -> dict[str, Any]:
    session = simulation_sessions.get(session_id)

    if session is None:
        raise ValueError("존재하지 않는 시뮬레이션 세션입니다.")

    if session["is_finished"]:
        raise ValueError("이미 종료된 시뮬레이션입니다.")

    scenario = find_scenario(session["scenario_id"])

    if scenario is None:
        raise ValueError("존재하지 않는 시나리오입니다.")

    current_stage_number = session["current_stage"]
    current_stage = scenario["stages"][current_stage_number - 1]

    # 1. 기존 규칙 기반 분석
    rule_analysis = analyze_stage_answer(
        answer=answer,
        stage=current_stage,
    )

    # 2. Gemini 기반 행동 의도 분석
    llm_analysis = analyze_with_llm(
        scenario_title=scenario["title"],
        stage_title=current_stage["title"],
        situation=current_stage["description"],
        answer=answer,
    )

    # 3. 두 분석 결과 병합
    analysis = merge_stage_analysis(
        rule_analysis=rule_analysis,
        llm_analysis=llm_analysis,
    )

    session["total_score"] += analysis["score"]
    session["stage_results"].append(
        {
            "stage": current_stage_number,
            "answer": answer,
            **analysis,
        }
    )

    is_finished = current_stage_number >= scenario["total_stages"]

    if is_finished:
        session["is_finished"] = True

        return {
            "session_id": session_id,
            "stage": current_stage_number,
            "stage_title": current_stage["title"],
            "stage_score": analysis["score"],
            "total_score": session["total_score"],
            "safe_actions": analysis["safe_actions"],
            "risky_actions": analysis["risky_actions"],
            "is_finished": True,
            "recommended_actions": current_stage["recommended_actions"],
        }

    next_stage_number = current_stage_number + 1
    next_stage = scenario["stages"][next_stage_number - 1]
    session["current_stage"] = next_stage_number

    return {
        "session_id": session_id,
        "stage": next_stage["stage"],
        "stage_title": next_stage["title"],
        "description": next_stage["description"],
        "messages": next_stage["messages"],
        "stage_score": analysis["score"],
        "total_score": session["total_score"],
        "safe_actions": analysis["safe_actions"],
        "risky_actions": analysis["risky_actions"],
        "total_stages": scenario["total_stages"],
        "is_finished": False,
    }


def get_session_result(session_id: str) -> dict[str, Any]:
    session = simulation_sessions.get(session_id)

    if session is None:
        raise ValueError("존재하지 않는 시뮬레이션 세션입니다.")

    scenario = find_scenario(session["scenario_id"])

    if scenario is None:
        raise ValueError("존재하지 않는 시나리오입니다.")

    score = session["total_score"]

    if score >= 61:
        risk_level = "low"
        risk_label = "안전한 대응"
    elif score >= 0:
        risk_level = "medium"
        risk_label = "주의가 필요한 대응"
    else:
        risk_level = "high"
        risk_label = "위험한 대응"

    safe_actions = [
        action
        for result in session["stage_results"]
        for action in result["safe_actions"]
    ]

    risky_actions = [
        action
        for result in session["stage_results"]
        for action in result["risky_actions"]
    ]

    return {
        "session_id": session_id,
        "scenario_id": scenario["id"],
        "scenario_title": scenario["title"],
        "score": score,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "stage_results": session["stage_results"],
        "safe_actions": safe_actions,
        "risky_actions": risky_actions,
        "recommended_actions": scenario["stages"][-1][
            "recommended_actions"
        ],
        "is_finished": session["is_finished"],
    }

def analyze_with_llm(
    scenario_title: str,
    stage_title: str,
    situation: str,
    answer: str,
) -> dict[str, Any]:
    llm_result = analyze_answer_with_llm(
        scenario_title=scenario_title,
        stage_title=stage_title,
        situation=situation,
        answer=answer,
    )

    score = 0
    safe_actions: list[str] = []
    risky_actions: list[str] = []

    seen_types: set[str] = set()

    for action in llm_result.get("actions", []):
        action_type = action.get("type")

        if action_type in seen_types:
            continue

        if action_type not in LLM_ACTION_SCORES:
            continue

        seen_types.add(action_type)
        score += LLM_ACTION_SCORES[action_type]

        label = LLM_ACTION_LABELS[action_type]

        if LLM_ACTION_SCORES[action_type] >= 0:
            safe_actions.append(label)
        else:
            risky_actions.append(label)

    return {
        "score": score,
        "safe_actions": safe_actions,
        "risky_actions": risky_actions,
        "risk_signals": llm_result.get("risk_signals", []),
        "llm_available": llm_result.get("llm_available", False),
    }

def merge_stage_analysis(
    rule_analysis: dict[str, Any],
    llm_analysis: dict[str, Any],
) -> dict[str, Any]:
    safe_actions = list(
        dict.fromkeys(
            rule_analysis["safe_actions"]
            + llm_analysis["safe_actions"]
        )
    )

    risky_actions = list(
        dict.fromkeys(
            rule_analysis["risky_actions"]
            + llm_analysis["risky_actions"]
        )
    )

    # 동일한 행동이 여러 분석 결과에 포함되더라도
    # 점수는 규칙 기반 점수만 사용해 중복 가산을 방지합니다.
    return {
        "score": rule_analysis["score"],
        "safe_actions": safe_actions,
        "risky_actions": risky_actions,
        "risk_signals": llm_analysis.get("risk_signals", []),
        "llm_score": llm_analysis.get("score", 0),
    }
