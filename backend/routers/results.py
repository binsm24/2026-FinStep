import json
import time

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import Diagnosis, Simulation, User, get_db
from services.auth_service import check_simulation_owner, require_user, trusted_write
from services.multi_stage_service import get_session_result

router = APIRouter(prefix='/api/results', tags=['results'])


class SaveResult(BaseModel):
    session_id: str


def summary(row):
    return {'id': row.id, 'scenario_title': row.scenario_title,
            'risk_label': row.risk_label, 'created_at': row.created_at,
            'risk_level': json.loads(row.snapshot).get('risk_level', 'unknown')}


@router.post('', dependencies=[Depends(trusted_write)])
def save_result(body: SaveResult, request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    existing = db.scalar(select(Diagnosis).where(Diagnosis.simulation_id == body.session_id))
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(404, '접근할 수 있는 결과가 없습니다.')
        return summary(existing)
    session = check_simulation_owner(body.session_id, request, user)
    try:
        result = get_session_result(body.session_id)
    except ValueError as error:
        raise HTTPException(409, '진단을 완료한 뒤 저장할 수 있습니다.') from error
    # Never trust a report or user_id supplied by the browser.
    row = Diagnosis(user_id=user.id, simulation_id=body.session_id,
                    scenario_title=result['scenario_title'], risk_label=result['risk_label'],
                    created_at=int(time.time()), snapshot=json.dumps(result, ensure_ascii=False))
    db.add(row)
    session['owner'] = 'user:' + user.id
    try:
        db.execute(update(Simulation).where(Simulation.id == body.session_id).values(
            snapshot=json.dumps(session, ensure_ascii=False), version=Simulation.version + 1
        ))
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.scalar(select(Diagnosis).where(Diagnosis.simulation_id == body.session_id, Diagnosis.user_id == user.id))
        if row is None:
            raise HTTPException(409, '이미 저장된 결과입니다.')
    # An anonymous report can only be claimed once, by its original browser.
    # The unique diagnosis row atomically binds this report to its claimant.
    return summary(row)


@router.get('')
def list_results(user: User = Depends(require_user), db: Session = Depends(get_db),
                 limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    rows = db.scalars(select(Diagnosis).where(Diagnosis.user_id == user.id)
                      .order_by(Diagnosis.created_at.desc(), Diagnosis.id.desc()).offset(offset).limit(limit + 1)).all()
    return {'items': [summary(row) for row in rows[:limit]], 'has_more': len(rows) > limit}


@router.get('/{result_id}')
def result_detail(result_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Diagnosis).where(Diagnosis.id == result_id, Diagnosis.user_id == user.id))
    if row is None:
        raise HTTPException(404, '접근할 수 있는 결과가 없습니다.')
    return {**summary(row), 'result': json.loads(row.snapshot)}
