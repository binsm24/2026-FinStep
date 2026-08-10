from typing import Any
from uuid import uuid4

from data.scenarios import MULTI_STAGE_SCENARIOS


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

    analysis = analyze_stage_answer(answer, current_stage)

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