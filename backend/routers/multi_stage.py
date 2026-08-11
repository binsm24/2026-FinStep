from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
from services.llm_service import (
    analyze_answer_with_llm,
    generate_next_response,
)

from services.multi_stage_service import (
    create_session,
    get_session_result,
    submit_stage_answer,
)


router = APIRouter(
    prefix="/api/multi-stage",
    tags=["multi-stage-simulators"],
)

class NextResponseRequest(BaseModel):
    scenario_title: str = Field(..., min_length=1)
    current_stage_title: str = Field(..., min_length=1)
    current_message: str = Field(..., min_length=1)
    user_answer: str = Field(..., min_length=2)
    next_stage_title: str = Field(..., min_length=1)
    next_stage_description: str = Field(..., min_length=1)
    next_stage_message: str = Field(..., min_length=1)

class LLMAnalysisRequest(BaseModel):
    scenario_title: str = Field(..., min_length=1)
    stage_title: str = Field(..., min_length=1)
    situation: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=2)

class StageAnswerRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=2)


@router.post("/{scenario_id}/start")
def start_simulation(scenario_id: str):
    try:
        return create_session(scenario_id)
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.post("/respond")
def respond_to_stage(request: StageAnswerRequest):
    try:
        return submit_stage_answer(
            session_id=request.session_id,
            answer=request.answer,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get("/sessions/{session_id}/result")
def get_simulation_result(session_id: str):
    try:
        return get_session_result(session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

# test 용 API
@router.post("/llm-test")
def test_llm_analysis(request: LLMAnalysisRequest):
    return analyze_answer_with_llm(
        scenario_title=request.scenario_title,
        stage_title=request.stage_title,
        situation=request.situation,
        answer=request.answer,
    )

@router.post("/next-response-test")
def test_next_response(request: NextResponseRequest):
    return generate_next_response(
        scenario_title=request.scenario_title,
        current_stage_title=request.current_stage_title,
        current_message=request.current_message,
        user_answer=request.user_answer,
        next_stage_title=request.next_stage_title,
        next_stage_description=request.next_stage_description,
        next_stage_message=request.next_stage_message,
    )
