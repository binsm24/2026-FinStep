from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from data.scenarios import SCENARIOS
from services.simulator_service import analyze_answer


router = APIRouter(prefix="/api/simulators", tags=["simulators"])


class AnalyzeRequest(BaseModel):
    scenario_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=2)


@router.get("/scenarios")
def get_scenarios():
    return SCENARIOS


@router.get("/scenarios/{scenario_id}")
def get_scenario(scenario_id: str):
    scenario = next(
        (item for item in SCENARIOS if item["id"] == scenario_id),
        None,
    )

    if scenario is None:
        raise HTTPException(
            status_code=404,
            detail="존재하지 않는 시나리오입니다.",
        )

    return scenario


@router.post("/analyze")
def analyze_simulation(request: AnalyzeRequest):
    try:
        result = analyze_answer(
            scenario_id=request.scenario_id,
            answer=request.answer,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    scenario = next(
        item for item in SCENARIOS
        if item["id"] == request.scenario_id
    )

    return {
        "scenario_id": request.scenario_id,
        "scenario_title": scenario["title"],
        **result,
        "recommended_actions": scenario["recommended_actions"],
    }
