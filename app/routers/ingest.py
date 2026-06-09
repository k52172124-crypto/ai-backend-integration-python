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

router = APIRouter(prefix="/rag", tags=["rag"])


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
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 7d2e4174509c0455ccb02294115c35f736377fdc
