from uuid import UUID, uuid4

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.db.models import Document, IngestJob, JobStatus
from app.deps import AppSettings, CurrentUser, DbSession
from app.schemas import DocumentOut, DocumentUploadResponse, JobOut
from app.services.ingest import process_document_job
from app.services.parsers import extract_text_from_bytes
from app.services.storage import ObjectStorage

router = APIRouter(tags=["documents"])


@router.post("/v1/documents", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    db: DbSession,
    user: CurrentUser,
    settings: AppSettings,
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    project_id: UUID | None = Form(default=None),
    visibility: str = Form(default="org"),
):
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Empty file")

    filename = file.filename or "upload.txt"
    content_type = file.content_type or "application/octet-stream"
    text = extract_text_from_bytes(raw, filename=filename, content_type=content_type)

    doc_id = uuid4()
    object_key = f"documents/{doc_id}/{filename}"

    storage = ObjectStorage(settings)
    try:
        storage.put_bytes(object_key, raw, content_type)
    except Exception:
        object_key = f"local/{doc_id}/{filename}"

    document = Document(
        id=doc_id,
        title=title or filename,
        filename=filename,
        content_type=content_type,
        object_key=object_key,
        project_id=project_id,
        uploaded_by=user.id,
        visibility=visibility,
        text_preview=text[:50_000],
    )
    db.add(document)
    db.flush()

    job = IngestJob(job_type="document", status=JobStatus.pending, document_id=document.id)
    db.add(job)
    db.commit()
    db.refresh(document)
    db.refresh(job)

    process_document_job(db, settings, job.id)
    db.refresh(job)

    return DocumentUploadResponse(document=document, job_id=job.id)


@router.get("/v1/documents", response_model=list[DocumentOut])
def list_documents(db: DbSession, _: CurrentUser):
    return db.query(Document).order_by(Document.created_at.desc()).limit(100).all()


@router.get("/v1/documents/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, db: DbSession, _: CurrentUser):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/v1/documents/{document_id}")
def delete_document(document_id: UUID, db: DbSession, user: CurrentUser):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    if user.role.value != "admin" and document.uploaded_by != user.id:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(document)
    db.commit()
    return {"ok": True}


@router.get("/v1/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: UUID, db: DbSession, _: CurrentUser):
    job = db.get(IngestJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job
