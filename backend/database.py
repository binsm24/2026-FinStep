"""Local SQLite by default; DATABASE_URL also accepts postgresql+psycopg://."""
import os
from functools import lru_cache
from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, String, Text, create_engine, event, text
from sqlalchemy.pool import NullPool
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from settings import BACKEND_DIR


class Base(DeclarativeBase):
    pass


class Simulation(Base):
    __tablename__ = 'simulations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=0)
    snapshot: Mapped[str] = mapped_column(Text)


class User(Base):
    __tablename__ = 'users'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    google_sub: Mapped[str] = mapped_column(String(255), unique=True)
    email: Mapped[str] = mapped_column(String(320))
    name: Mapped[str] = mapped_column(String(200))


class LoginSession(Base):
    __tablename__ = 'login_sessions'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class LoginChallenge(Base):
    __tablename__ = 'login_challenges'
    token_hash: Mapped[str] = mapped_column(String(64), primary_key=True)
    nonce_hash: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[int] = mapped_column(Integer, index=True)


class Diagnosis(Base):
    __tablename__ = 'diagnoses'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(ForeignKey('users.id'), index=True)
    simulation_id: Mapped[str] = mapped_column(String(36), unique=True)
    scenario_title: Mapped[str] = mapped_column(String(100))
    risk_label: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[int] = mapped_column(Integer, index=True)
    snapshot: Mapped[str] = mapped_column(Text)


@lru_cache(maxsize=1)
def get_engine():
    url = os.getenv('DATABASE_URL', '').strip()
    if not url:
        if os.getenv('VERCEL'):
            raise RuntimeError('DATABASE_URL is required on Vercel')
        folder = BACKEND_DIR / 'storage'
        folder.mkdir(exist_ok=True)
        url = f"sqlite:///{(folder / 'finstep.db').as_posix()}"
    if url.startswith('postgres://'):
        url = url.replace('postgres://', 'postgresql+psycopg://', 1)
    elif url.startswith('postgresql://'):
        url = url.replace('postgresql://', 'postgresql+psycopg://', 1)
    kwargs = {'connect_args': {'check_same_thread': False, 'timeout': 15}} if url.startswith('sqlite:') else {}
    if url.startswith('postgresql+psycopg:'):
        kwargs = {'poolclass': NullPool, 'connect_args': {'connect_timeout': 10, 'prepare_threshold': None}}
    engine = create_engine(url, pool_pre_ping=True, **kwargs)
    if url.startswith('sqlite:'):
        @event.listens_for(engine, 'connect')
        def sqlite_foreign_keys(connection, _):
            connection.execute('PRAGMA foreign_keys=ON')
    return engine


def init_db():
    engine = get_engine()
    with engine.begin() as connection:
        if engine.dialect.name == 'postgresql':
            # Serialize first-start DDL when multiple serverless instances start.
            connection.execute(text('SELECT pg_advisory_xact_lock(724916032)'))
        Base.metadata.create_all(connection)


def get_db():
    with Session(get_engine()) as db:
        yield db
