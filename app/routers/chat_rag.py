<<<<<<< HEAD
"""PDF 업로드 인제스트 /ingest 라우트.

흐름:
  1. UploadFile 로 PDF 바이트 수신
  2. 임시 파일에 저장 후 PyPDFLoader 로 페이지 단위 파싱
  3. RecursiveCharacterTextSplitter 로 청킹
  4. 각 청크에 출처 메타데이터(source=파일명, page=페이지)를 부여
  5. 공유 Chroma 벡터스토어에 add_documents 로 누적 저장

핵심 패턴:
- PDF 파싱·임베딩은 CPU/네트워크 블로킹 작업이므로 run_in_threadpool 로 감싸
  이벤트 루프가 다른 요청을 처리하도록 둡니다.
- get_vectorstore() 와 동일한 싱글톤을 쓰므로 업로드 직후 바로 검색에 반영됩니다.
"""

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..dependencies import RagSettings, get_rag_settings, get_vectorstore
from ..schemas import IngestResponse
=======
"""CrewAI RAG /chat/rag 라우트.

흐름:
- @tool 로 정의한 '회사 문서 검색 도구'가 LangChain retriever 를 감쌉니다
- 인사팀 에이전트가 이 도구로 벡터 DB(POST /ingest 로 적재된 PDF)를 검색해
  근거에 기반한 답변을 생성합니다

핵심 패턴:
- 검색 도구 안에서 get_retriever() 를 lazy 호출합니다. 모듈 import 시점에
  벡터스토어를 만들지 않으므로 OpenAI 키 없이도 import/테스트가 가능합니다.
- CrewAI 는 kickoff_async() 로 호출해 FastAPI 이벤트 루프를 막지 않습니다.
"""

from crewai import Agent, Crew, Process, Task
from crewai import LLM as CrewLLM
from crewai.tools import tool
from fastapi import APIRouter, Depends

from ..dependencies import Settings, get_retriever, get_settings
from ..schemas import ChatResponse, RagRequest
>>>>>>> 7d2e4174509c0455ccb02294115c35f736377fdc

router = APIRouter(prefix="/rag", tags=["rag"])


<<<<<<< HEAD
def _ingest_pdf(
    data: bytes,
    filename: str,
    store: Chroma,
    settings: RagSettings,
) -> IngestResponse:
    """PDF 바이트를 청킹·임베딩하여 벡터스토어에 저장한다(동기, 스레드풀에서 실행)."""
    # PyPDFLoader 는 파일 경로를 요구하므로 임시 파일에 기록
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(data)
        tmp_path = Path(tmp.name)

    try:
        pages = PyPDFLoader(str(tmp_path)).load()
    finally:
        tmp_path.unlink(missing_ok=True)

    if not pages:
        raise HTTPException(status_code=422, detail="PDF에서 텍스트를 추출하지 못했습니다.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(pages)

    # 출처 메타데이터를 원본 파일명으로 정리 (검색 결과에 'source p.N' 표기용)
    for chunk in chunks:
        chunk.metadata["source"] = filename

    store.add_documents(chunks)

    return IngestResponse(
        filename=filename,
        pages=len(pages),
        chunks_added=len(chunks),
        total_chunks=store._collection.count(),
    )


@router.post("/ingest")
async def ingest(
    file: UploadFile = File(..., description="임베딩할 PDF 파일"),
    settings: RagSettings = Depends(get_rag_settings),
) -> IngestResponse:
    """PDF를 업로드하면 청킹·임베딩하여 벡터 DB에 추가합니다."""
    filename = file.filename or "uploaded.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=415, detail="PDF 파일만 업로드할 수 있습니다.")

    data = await file.read()
    if not data:
        raise HTTPException(status_code=422, detail="빈 파일입니다.")

    # 블로킹 작업(파싱·임베딩)은 스레드풀에서 실행해 이벤트 루프를 막지 않습니다
    return await run_in_threadpool(
        _ingest_pdf, data, filename, get_vectorstore(), settings
    )
=======
@tool("company_doc_search")
def company_doc_search(query: str) -> str:
    """회사 내부 문서(규정, 매뉴얼 등)에서 질문과 관련된 내용을 검색합니다."""
    # retriever 가 질문과 가장 유사한 청크 k개를 벡터 DB에서 찾아옵니다
    retriever = get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "관련 문서를 찾지 못했습니다. 먼저 POST /ingest 로 문서를 업로드하세요."
    # 출처(파일명)와 함께 본문을 반환해 에이전트가 근거를 인용할 수 있게 합니다
    return "\n\n".join(
        f"[출처: {d.metadata.get('source', '?')}]\n{d.page_content}" for d in docs
    )


def _build_crew(question: str, settings: Settings) -> Crew:
    """검색 도구를 장착한 인사팀 에이전트 Crew를 구성합니다."""
    llm = CrewLLM(
        model=f"openai/{settings.model_name}",
        api_key=settings.openai_api_key,
    )

    policy_agent = Agent(
        role="인사팀 에이전트",
        goal="사내 규정에 맞게 직원의 질문에 정확히 답변한다",
        backstory="사내 모든 규정을 숙지하고 있는 친절한 인사팀 담당자입니다.",
        tools=[company_doc_search],
        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    answer_task = Task(
        description=(
            f"직원의 질문에 답하세요: '{question}'\n"
            "반드시 '회사 문서 검색 도구'로 사내 문서를 먼저 검색하고, "
            "검색된 근거에 기반해 한국어로 답하세요. "
            "문서에 없는 내용은 추측하지 말고 모른다고 답하세요."
        ),
        expected_output="사내 문서 근거에 기반한 한국어 답변",
        agent=policy_agent,
    )

    return Crew(
        agents=[policy_agent],
        tasks=[answer_task],
        process=Process.sequential,
        verbose=False,
    )


@router.post("/chat", response_model=ChatResponse)
async def chat_rag(
    req: RagRequest,
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    """CrewAI 인사팀 에이전트가 벡터 DB를 검색해 답합니다."""
    crew = _build_crew(req.question, settings)
    result = await crew.kickoff_async()
    return ChatResponse(answer=str(result), model=f"rag-{settings.model_name}")
>>>>>>> 7d2e4174509c0455ccb02294115c35f736377fdc
