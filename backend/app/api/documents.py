"""资料管理 API：上传 / 列表 / 详情 / 删除。"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal, get_db
from ..models import Chapter, Document
from ..schemas import DocumentDetail, DocumentOut
from ..services import chunker, parsers
from ..services.vector_store import VectorStore

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {"pdf", "docx", "md", "txt"}

# 魔数校验：扩展名之外的内容检查，防止任意文件伪装
_MAGIC = {
    "pdf": (b"%PDF",),
    "docx": (b"PK\x03\x04",),
}


def _ext(file_name: str) -> str:
    return file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""


def _check_magic(ext: str, head: bytes) -> None:
    for sig in _MAGIC.get(ext, ()):
        if head.startswith(sig):
            return
    if ext in _MAGIC:
        raise HTTPException(status_code=400, detail=f"文件内容与 .{ext} 格式不符")


def _process_document(doc_id: int, upload_path: Path) -> None:
    """后台任务：解析 → 章节入库 → 分块 → 向量化。

    使用独立数据库会话（不依赖请求级 session），并在每步复查文档仍存在，
    避免与删除操作竞态产生孤儿数据。
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if doc is None:
            return
        parsed = parsers.parse_document(str(upload_path), doc.file_type)

        doc = db.get(Document, doc_id)
        if doc is None:
            return  # 处理期间被删除
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
        chunks = [c for c in chunks if c.text.strip()]  # 过滤空块

        doc = db.get(Document, doc_id)
        if doc is None:
            return
        # 幂等：先清理该文档的旧向量再写入（防止重复处理残留）
        store = VectorStore()
        store.delete_document(doc.id)
        n = store.add_chunks(doc.id, doc.original_name, chunks)
        doc.status = "ready"
        doc.chunk_count = n
        doc.page_count = parsed.page_count
        doc.error = ""
        db.commit()
    except Exception as e:  # noqa: BLE001 - 记录失败原因供前端展示
        db.rollback()
        doc = db.get(Document, doc_id)
        if doc is not None:
            doc.status = "failed"
            doc.error = str(e)[:1000]
            db.commit()
    finally:
        db.close()


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

    max_bytes = settings.max_upload_mb * 1024 * 1024
    size = 0
    head = b""
    try:
        with open(upload_path, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"文件超过大小限制（{settings.max_upload_mb} MB）",
                    )
                if len(head) < 8:
                    head = (head + chunk)[:8]
                f.write(chunk)
        if size == 0:
            raise HTTPException(status_code=400, detail="文件内容为空")
        _check_magic(ext, head)
    except Exception:
        upload_path.unlink(missing_ok=True)
        raise

    doc = Document(
        original_name=name,
        stored_name=stored_name,
        file_type=ext,
        size_bytes=size,
        status="pending",
    )
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        upload_path.unlink(missing_ok=True)  # 入库失败时清理已写文件，避免孤儿
        raise

    background.add_task(_process_document, doc.id, upload_path)
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


@router.get("/{doc_id}/content")
def get_document_content(doc_id: int, db: Session = Depends(get_db)):
    """返回资料全文（按章节组织，含页码），用于预览。"""
    doc = db.get(Document, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="资料不存在")
    if doc.status != "ready":
        raise HTTPException(status_code=400, detail=f"资料未处理完成（当前状态: {doc.status}）")
    upload_path = Path(settings.upload_dir) / doc.stored_name
    if not upload_path.exists():
        raise HTTPException(status_code=404, detail="原始文件已丢失")
    parsed = parsers.parse_document(str(upload_path), doc.file_type)
    return {
        "document_id": doc.id,
        "original_name": doc.original_name,
        "file_type": doc.file_type,
        "page_count": parsed.page_count,
        "sections": [
            {"path": s.path, "page": s.page, "text": s.text}
            for s in parsed.sections
        ],
    }


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