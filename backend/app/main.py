from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import targets, scans, workers
from app.db.session import engine
from app.models.base import Base
# 모델들을 import해야 Base.metadata에 등록됨
# 모델들을 import해야 Base.metadata에 등록됨
from app.models import target, scan, subdomain, port, technology, path

# DB 테이블 자동 생성 (개발용)
# 실제 프로덕션에서는 Alembic 사용 권장
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

app = FastAPI(
    title="BG-Scanner API",
    description="Bug Bounty Scanner API",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    await create_tables()

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # 개발 중에는 모든 오리진 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return {"status": "ok", "message": "BG-Scanner API is running"}

# API 라우터 등록
app.include_router(targets.router, prefix="/api/targets", tags=["targets"])
app.include_router(scans.router, prefix="/api/scans", tags=["scans"])
app.include_router(workers.router, prefix="/api/workers", tags=["workers"])
