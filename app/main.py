"""FastAPI 애플리케이션 진입점.

라우트 구성:
- GET  /health        : 헬스 체크
- POST /echo          : Pydantic 검증 시연
- POST /chat          : LangChain 단일 체인
- POST /chat/crew     : CrewAI 멀티에이전트
- GET  /docs          : Swagger UI
- GET  /redoc         : ReDoc
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routers import chat_rag, ingest
from .errors import handle_unexpected
from .middleware import add_process_time
from .routers import chat_crew, chat_langchain
from .schemas import ChatRequest, ChatResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(
    title="AI Backend",
    description="Day1 산출물 — LangChain/CrewAI를 노출하는 FastAPI",
    version="1.0.0",
)

# 미들웨어 — 등록 순서 역순으로 실행됩니다
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(add_process_time)

# 예외 핸들러
app.add_exception_handler(Exception, handle_unexpected)

# 라우터
app.include_router(chat_langchain.router)
app.include_router(chat_crew.router)


@app.get("/health", tags=["meta"])
def health() -> dict[str, str]:
    """헬스 체크 — Docker/k8s liveness 용도."""
    return {"status": "ok"}


@app.post("/echo", response_model=ChatResponse, tags=["meta"])
def echo(req: ChatRequest) -> ChatResponse:
    """Pydantic v2 검증 시연용 echo 엔드포인트."""
    return ChatResponse(answer=req.prompt, model="echo-1")
