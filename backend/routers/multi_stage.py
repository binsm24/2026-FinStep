from typing import Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from services.auth_service import optional_user, trusted_write, new_simulation_owner, check_simulation_owner
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
    branch: Literal["safe", "risky"]
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
    answer: str = Field(..., min_length=2, max_length=500)
    request_id: str | None = Field(default=None, min_length=1, max_length=64)
    expected_stage: int | None = Field(default=None, ge=1, le=4)


@router.post("/{scenario_id}/start", dependencies=[Depends(trusted_write)])
def start_simulation(scenario_id: str, request: Request, response: Response, user=Depends(optional_user)):
    try:
        return create_session(scenario_id, owner=new_simulation_owner(request, response, user))
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error


@router.post("/respond", dependencies=[Depends(trusted_write)])
def respond_to_stage(request: StageAnswerRequest, http_request: Request, user=Depends(optional_user)):
    check_simulation_owner(request.session_id, http_request, user)
    try:
        return submit_stage_answer(
            session_id=request.session_id,
            answer=request.answer,
            request_id=request.request_id,
            expected_stage=request.expected_stage,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


@router.get("/sessions/{session_id}/result")
def get_simulation_result(session_id: str, request: Request, user=Depends(optional_user)):
    check_simulation_owner(session_id, request, user)
    try:
        return get_session_result(session_id)
    except ValueError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

# test 용 API
@router.post("/llm-test", dependencies=[Depends(trusted_write)])
def test_llm_analysis(request: LLMAnalysisRequest):
    return analyze_answer_with_llm(
        scenario_title=request.scenario_title,
        stage_title=request.stage_title,
        situation=request.situation,
        answer=request.answer,
    )

@router.post("/next-response-test", dependencies=[Depends(trusted_write)])
def test_next_response(request: NextResponseRequest):
    return generate_next_response(
        scenario_title=request.scenario_title,
        current_stage_title=request.current_stage_title,
        current_message=request.current_message,
        user_answer=request.user_answer,
        next_stage_title=request.next_stage_title,
        next_stage_description=request.next_stage_description,
        next_stage_message=request.next_stage_message,
        branch=request.branch,
    )
