"""资料管理 API：上传 / 列表 / 详情 / 删除。"""
from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import get_db
from ..models import Chapter, Document
from ..schemas import DocumentDetail, DocumentOut
from ..services import chunker, parsers
from ..services.vector_store import VectorStore

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "md": "text/markdown",
    "txt": "text/plain",
}


def _ext(file_name: str) -> str:
    return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def _process_document(db: Session, doc_id: int, upload_path: Path) -> None:
    """后台任务：解析 → 章节入库 → 分块 → 向量化。"""
    doc = db.get(Document, doc_id)
    if doc is None:
        return
    try:
        parsed = parsers.parse_document(str(upload_path), doc.file_type)
        for ch in doc.chapters:
            db.delete(ch)
        for s in parsed.sections:
            db.add(
                Chapter(
                    document_id=doc.id,
                    title=s.title,
                    level=s.level,
                    path=s.path,
                    page=s.page,
                    order_index=s.order,
                )
            )
        chunks = chunker.chunk_document(parsed, settings.chunk_size, settings.chunk_overlap)
        store = VectorStore()
        n = store.add_chunks(doc.id, doc.original_name, chunks)
        doc.status = "ready"
        doc.chunk_count = n
        doc.page_count = parsed.page_count
        doc.error = ""
    except Exception as e:  # noqa: BLE001 - 记录失败原因供前端展示
        doc.status = "failed"
        doc.error = str(e)[:1000]
    db.commit()


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    name = file.filename or "unnamed"
    ext = _ext(name)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: .{ext}（支持 pdf/docx/md/txt）")
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    upload_path = upload_root / stored_name

    size = 0
    with open(upload_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            f.write(chunk)

    doc = Document(
        original_name=name,
        stored_name=stored_name,
        file_type=ext,
        size_bytes=size,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background.add_task(_process_document, db, doc.id, upload_path)
    return doc


@router.get("", response_model=list[DocumentOut])
def list_documents(db: Session = Depends(get_db)):
    return db.query(Document).order_by(Document.created_at.desc()).all()


@router.get("/{doc_id}", response_model=DocumentDetail)
def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    return doc


@router.delete("/{doc_id}")
def delete_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    try:
        VectorStore().delete_document(doc_id)
    except Exception:  # noqa: BLE001 - 向量删除失败不阻塞资料删除
        pass
    upload_path = Path(settings.upload_dir) / doc.stored_name
    if upload_path.exists():
        upload_path.unlink()
    db.delete(doc)
    db.commit()
    return {"ok": True}
