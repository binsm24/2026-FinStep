from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from settings import allowed_origins
from database import init_db
from web import mount_frontend

import os
from dotenv import load_dotenv

from routers.simulator import router as simulator_router
from routers.multi_stage import router as multi_stage_router

from routers.learning import router as learning_router
from routers.auth import router as auth_router
from routers.results import router as results_router

load_dotenv()

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield


app = FastAPI(
    lifespan=lifespan,
    title="FinStep API",
    description="대학생 금융 위험 대응 시뮬레이터 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulator_router)
app.include_router(multi_stage_router)
app.include_router(learning_router)
app.include_router(auth_router)
app.include_router(results_router)


@app.middleware('http')
async def private_responses(request, call_next):
    response = await call_next(request)
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(SQLAlchemyError)
async def database_unavailable(request, error):
    return JSONResponse(status_code=503, content={'detail': '저장소에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요.'})

@app.get("/")
def read_root():
    return {
        "service": "FinStep",
        "message": "FinStep API is running",
    }

@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }

@app.get("/health/llm")
def llm_health_check():
    return {
        "configured": bool(os.getenv("GEMINI_API_KEY")),
        "provider": "gemini",
        "model": os.getenv(
            "GEMINI_MODEL",
            "gemini-3.5-flash",
        ),
    }


# Register after the API routes so the SPA cannot shadow them.
mount_frontend(app)
