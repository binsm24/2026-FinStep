from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException

from services.multi_stage_service import (
    create_session,
    get_session_result,
    submit_stage_answer,
)


router = APIRouter(
    prefix="/api/multi-stage",
    tags=["multi-stage-simulators"],
)


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
