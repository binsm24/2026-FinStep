"""Database snapshots with optimistic concurrency across serverless instances."""
import json

from sqlalchemy import update
from sqlalchemy.orm import Session

from database import Simulation, get_engine


def create_session_snapshot(data):
    with Session(get_engine()) as db:
        db.add(Simulation(id=data['session_id'], version=0, snapshot=json.dumps(data, ensure_ascii=False)))
        db.commit()


def load_session(session_id):
    with Session(get_engine()) as db:
        row = db.get(Simulation, session_id)
        return (json.loads(row.snapshot), row.version) if row else (None, None)


def save_session(data, version):
    with Session(get_engine()) as db:
        result = db.execute(update(Simulation).where(
            Simulation.id == data['session_id'], Simulation.version == version
        ).values(snapshot=json.dumps(data, ensure_ascii=False), version=version + 1))
        db.commit()
        return result.rowcount == 1


def get_session(session_id):
    return load_session(session_id)[0]
