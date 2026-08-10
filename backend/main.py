from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import os
from dotenv import load_dotenv

from routers.simulator import router as simulator_router
from routers.multi_stage import router as multi_stage_router

load_dotenv()

app = FastAPI(
    title="FinStep API",
    description="대학생 금융 위험 대응 시뮬레이터 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulator_router)
app.include_router(multi_stage_router)

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
