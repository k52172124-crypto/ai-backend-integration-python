"""요청·응답 Pydantic v2 스키마.

엔드포인트마다 의미에 맞는 요청 스키마를 둡니다.
- /chat       : 자유 질문(prompt)을 받는 ChatRequest
- /chat/crew  : 리서치 주제(topic)를 받는 CrewRequest
잘못된 타입은 라우트 진입 전에 422로 차단됩니다.
"""

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """LangChain /chat 요청 본문.

    사용자 식별은 Spring 게이트웨이가 JWT로 처리하므로
    Python은 prompt만 받습니다. (Spring이 보내는 user_id 등 추가 필드는
    Pydantic이 기본 무시하므로 호환에 문제 없습니다.)
    """

    prompt: str = Field(..., min_length=1, max_length=2000, description="사용자 질문")

    model_config = {
        "json_schema_extra": {
            "example": {"prompt": "안녕하세요"}
        }
    }


class CrewRequest(BaseModel):
    """CrewAI /chat/crew 요청 본문.

    자유 질문이 아니라 리서처·라이터가 협업할 '주제'를 받으므로
    필드명을 topic으로 두어 의미를 명확히 합니다.
    """

    topic: str = Field(..., min_length=1, max_length=200, description="리서치 주제")

    model_config = {
        "json_schema_extra": {
            "example": {"topic": "파이썬"}
        }
    }


class ChatResponse(BaseModel):
    """채팅 응답 본문."""

    answer: str = Field(..., description="모델 응답 본문")
    model: str = Field(..., description="실제 사용된 모델 식별자")


class IngestResponse(BaseModel):
    """PDF 인제스트 결과 응답.

    업로드한 문서가 몇 개의 청크로 나뉘어 벡터 DB에 저장됐는지 알려줍니다.
    """

    filename: str = Field(..., description="업로드된 파일명")
    pages: int = Field(..., description="PDF에서 추출된 페이지 수")
    chunks_added: int = Field(..., description="벡터 DB에 추가된 청크 수")
    total_chunks: int = Field(..., description="저장소 전체 청크 수(누적)")


class RagRequest(BaseModel):
    """RAG /chat/rag 요청 본문.

    업로드된 사내 문서(벡터 DB)에서 근거를 찾아 답할 '질문'을 받습니다.
    """

    question: str = Field(
        ..., min_length=1, max_length=500, description="사내 문서에 대한 질문"
    )

    model_config = {
        "json_schema_extra": {
            "example": {"question": "문의는 어디로 하면 되나요?"}
        }
    }