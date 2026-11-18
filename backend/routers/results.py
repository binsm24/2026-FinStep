import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import Diagnosis, Simulation, User, get_db
from services.auth_service import require_user, trusted_write
from services.result_archive import archive_result

router = APIRouter(prefix='/api/results', tags=['results'])


class SaveResult(BaseModel):
    session_id: str


def summary(row):
    report = json.loads(row.snapshot)
    return {'id': row.id, 'scenario_title': row.scenario_title,
            'risk_label': row.risk_label, 'created_at': row.created_at,
            'risk_level': report.get('risk_level', 'unknown'),
            'score': report.get('score'),
            'scoring_version': report.get('scoring_version', 'legacy-v0')}


@router.post('', dependencies=[Depends(trusted_write)])
def save_result(body: SaveResult, request: Request, user: User = Depends(require_user), db: Session = Depends(get_db)):
    return summary(archive_result(body.session_id, request, user, db))


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


@router.delete('/{result_id}', dependencies=[Depends(trusted_write)])
def delete_result(result_id: str, user: User = Depends(require_user), db: Session = Depends(get_db)):
    row = db.scalar(select(Diagnosis).where(Diagnosis.id == result_id, Diagnosis.user_id == user.id))
    if row is None:
        raise HTTPException(404, '접근할 수 있는 결과가 없습니다.')
    simulation = db.scalar(select(Simulation).where(Simulation.id == row.simulation_id).with_for_update())
    db.delete(row)
    if simulation is not None:
        db.delete(simulation)
    db.commit()
    return {'deleted': True}
