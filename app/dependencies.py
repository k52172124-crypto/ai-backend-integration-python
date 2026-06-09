"""의존성 주입 — Settings와 LLM 클라이언트.

요청마다 ChatOpenAI 인스턴스를 새로 만들면 비효율적이므로
@lru_cache로 캐시된 팩토리를 Depends로 노출합니다.

※ 아래쪽 "RAG (심화)" 섹션은 PDF 업로드/검색 기능 전용 설정·팩토리입니다.
   Day1 기본 과정에서는 Settings / get_settings / get_llm 까지만 보면 됩니다.
"""

from functools import lru_cache
from pathlib import Path

from langchain_openai import ChatOpenAI
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """환경변수 기반 설정.

    .env 파일이 있으면 자동 로드합니다.
    """

    openai_api_key: str
    model_name: str = "gpt-5-nano"
    port: int = 8000
    request_timeout: float = 30.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # RAG 전용 변수(embedding_model 등)는 RagSettings 담당이므로 무시
    )


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤. 첫 호출 시 1회만 생성됩니다."""
    return Settings()


@lru_cache
def get_llm() -> ChatOpenAI:
    """ChatOpenAI 싱글톤.

    Depends(get_llm)으로 주입받으면 요청마다 객체가 재사용됩니다.
    """
    settings = get_settings()
    return ChatOpenAI(
        model=settings.model_name,
        api_key=settings.openai_api_key,
        timeout=settings.request_timeout,
    )


# ──────────────────────────────────────────────────────────────────────────
# RAG (심화) — PDF 업로드/검색 전용. 기본 과정에서는 다루지 않습니다.
# 기존 Settings 를 건드리지 않도록 RAG 설정은 별도 클래스로 분리합니다.
# ──────────────────────────────────────────────────────────────────────────

from langchain_chroma import Chroma  # noqa: E402
from langchain_core.vectorstores import VectorStoreRetriever  # noqa: E402
from langchain_openai import OpenAIEmbeddings  # noqa: E402

# 프로젝트 루트 (app/ 의 상위 디렉터리)
ROOT = Path(__file__).resolve().parent.parent


class RagSettings(BaseSettings):
    """RAG 파이프라인 설정 — 임베딩·벡터 DB·청킹.

    기본 Settings 와 같은 .env 를 읽되, RAG 관련 값만 담습니다.
    """

    openai_api_key: str  # 임베딩 호출에도 OpenAI 키가 필요합니다
    embedding_model: str = "text-embedding-3-small"
    chroma_dir: str = str(ROOT / "chroma_db")
    rag_top_k: int = 3
    chunk_size: int = 500
    chunk_overlap: int = 50

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Settings 쪽 변수(model_name 등)는 무시
    )


@lru_cache
def get_rag_settings() -> RagSettings:
    """RagSettings 싱글톤."""
    return RagSettings()


@lru_cache
def get_embeddings() -> OpenAIEmbeddings:
    """OpenAIEmbeddings 싱글톤.

    인제스트(저장)와 검색(질의)이 같은 임베딩 모델을 써야 하므로
    한 곳에서 만들어 양쪽이 공유합니다.
    """
    settings = get_rag_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.openai_api_key,
    )


@lru_cache
def get_vectorstore() -> Chroma:
    """Chroma 벡터스토어 싱글톤.

    persist_directory를 가리키므로 서버 재시작 후에도 데이터가 유지됩니다.
    디렉터리가 비어 있으면 빈 컬렉션으로 시작하고, POST /rag/ingest 가 채웁니다.
    인제스트(add_documents)와 검색(as_retriever)이 동일 인스턴스를 공유해야
    업로드 직후 바로 검색에 반영됩니다.
    """
    settings = get_rag_settings()
    return Chroma(
        persist_directory=settings.chroma_dir,
        embedding_function=get_embeddings(),
    )


def get_retriever() -> VectorStoreRetriever:
    """벡터스토어 retriever.

    질의와 가장 유사한 청크 rag_top_k개를 반환하도록 설정합니다.
    벡터스토어는 캐시된 싱글톤이지만, retriever는 가벼운 래퍼라
    호출마다 새로 만들어도 무방합니다.
    """
    settings = get_rag_settings()
    return get_vectorstore().as_retriever(
        search_kwargs={"k": settings.rag_top_k},
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 7d2e4174509c0455ccb02294115c35f736377fdc
