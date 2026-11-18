"""Idempotent archive writes for authenticated completions; no guest claiming."""
import json
import time

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from database import Diagnosis, Simulation
from services.auth_service import check_simulation_owner
from services.multi_stage_service import get_session_result


def archive_result(session_id, request, user, db):
    # Serialize saving/deleting the same simulation on PostgreSQL. A removed
    # simulation must not be recreated by a delayed automatic-save request.
    simulation = db.scalar(select(Simulation).where(Simulation.id == session_id).with_for_update())
    if simulation is None:
        raise HTTPException(404, '접근할 수 있는 시뮬레이션이 없습니다.')
    existing = db.scalar(select(Diagnosis).where(Diagnosis.simulation_id == session_id))
    if existing:
        if existing.user_id != user.id:
            raise HTTPException(404, '접근할 수 있는 결과가 없습니다.')
        return existing
    session = check_simulation_owner(session_id, request, user)
    if 'completion_user_id' in session:
        if session['completion_user_id'] != user.id:
            raise HTTPException(403, '비로그인 상태로 완료한 결과는 보관함에 저장되지 않습니다.')
    elif session.get('owner') != 'user:' + user.id:
        # Legacy completed guest sessions cannot be claimed retroactively.
        raise HTTPException(403, '비로그인 상태로 완료한 결과는 보관함에 저장되지 않습니다.')
    try:
        result = get_session_result(session_id)
    except ValueError as error:
        raise HTTPException(409, '진단을 완료한 뒤 저장할 수 있습니다.') from error
    row = Diagnosis(user_id=user.id, simulation_id=session_id,
                    scenario_title=result['scenario_title'], risk_label=result['risk_label'],
                    created_at=int(time.time()), snapshot=json.dumps(result, ensure_ascii=False))
    db.add(row)
    session['owner'] = 'user:' + user.id
    try:
        db.execute(update(Simulation).where(Simulation.id == session_id).values(
            snapshot=json.dumps(session, ensure_ascii=False), version=Simulation.version + 1))
        db.commit()
    except IntegrityError:
        db.rollback()
        row = db.scalar(select(Diagnosis).where(Diagnosis.simulation_id == session_id,
                                               Diagnosis.user_id == user.id))
        if row is None:
            raise HTTPException(409, '이미 저장된 결과입니다.')
    return row
