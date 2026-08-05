from __future__ import annotations

import re
import uuid
from uuid import UUID

from sqlalchemy.orm import Session

from app.config import Settings
from app.db.models import Document, DocumentChunk, IngestJob, JobStatus, Meeting
from app.services.embeddings import get_embedder
from app.services.graph import GraphStore
from app.services.parsers import normalize_whitespace
from app.services.vector import VectorStore


def chunk_text(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    text = normalize_whitespace(text)
    if not text:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        chunks.append(text[start:end])
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def extract_entities(text: str) -> dict:
    """Lightweight heuristic extraction for MVP scaffolding."""
    projects = re.findall(r"\bProject\s+([A-Z][A-Za-z0-9_-]+)", text)
    people = re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", text)
    decisions = re.findall(r"(?i)decision[:\s]+(.{10,120})", text)
    tasks = re.findall(r"(?i)(?:action item|todo|follow[- ]up)[:\s]+(.{10,120})", text)
    return {
        "projects": list(dict.fromkeys(projects))[:10],
        "people": list(dict.fromkeys(people))[:10],
        "decisions": [d.strip() for d in decisions[:5]],
        "tasks": [t.strip() for t in tasks[:8]],
    }


def process_document_job(
    db: Session,
    settings: Settings,
    job_id: UUID,
    *,
    graph: GraphStore | None = None,
    vector_store: VectorStore | None = None,
) -> IngestJob:
    job = db.get(IngestJob, job_id)
    if not job or not job.document_id:
        raise ValueError("Job or document missing")

    job.status = JobStatus.running
    job.error = None
    db.commit()

    owns_graph = graph is None
    graph = graph or GraphStore(settings)
    vector_store = vector_store or VectorStore(settings)

    try:
        document = db.get(Document, job.document_id)
        if not document:
            raise ValueError("Document not found")

        text = document.text_preview or ""
        chunks = chunk_text(text)
        embedder = get_embedder(settings)
        vectors = embedder.embed(chunks) if chunks else []

        graph.upsert_node(
            "Document",
            str(document.id),
            {"title": document.title, "source_system": document.source_system},
        )
        if document.project_id:
            graph.upsert_node(
                "Project",
                str(document.project_id),
                {"name": str(document.project_id)},
            )
            graph.upsert_edge(
                "Document",
                str(document.id),
                "Project",
                str(document.project_id),
                "BELONGS_TO",
            )

        entities = extract_entities(text)
        for project_name in entities["projects"]:
            pid = f"project:{project_name.lower()}"
            graph.upsert_node("Project", pid, {"name": project_name})
            graph.upsert_edge("Document", str(document.id), "Project", pid, "RELATED_TO")

        for person in entities["people"]:
            eid = f"employee:{person.lower().replace(' ', '-')}"
            graph.upsert_node("Employee", eid, {"name": person})
            graph.upsert_edge("Employee", eid, "Document", str(document.id), "CREATED")

        db.query(DocumentChunk).filter(DocumentChunk.document_id == document.id).delete()
        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(uuid.uuid5(document.id, f"chunk-{idx}"))
            row = DocumentChunk(
                document_id=document.id,
                chunk_index=idx,
                content=chunk,
                token_count=len(chunk.split()),
                vector_id=point_id,
            )
            db.add(row)
            vector_store.upsert(
                point_id=point_id,
                vector=vector,
                payload={
                    "document_id": str(document.id),
                    "title": document.title,
                    "snippet": chunk[:400],
                    "project_id": str(document.project_id) if document.project_id else None,
                    "visibility": document.visibility,
                    "type": "document",
                },
            )

        job.status = JobStatus.completed
        job.stats = {
            "chunks_indexed": len(chunks),
            "entities": {k: len(v) for k, v in entities.items()},
        }
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        db.commit()
        db.refresh(job)
        return job
    finally:
        if owns_graph:
            try:
                graph.close()
            except Exception:
                pass


def process_meeting_job(
    db: Session,
    settings: Settings,
    job_id: UUID,
    *,
    graph: GraphStore | None = None,
    vector_store: VectorStore | None = None,
) -> IngestJob:
    job = db.get(IngestJob, job_id)
    if not job or not job.meeting_id:
        raise ValueError("Job or meeting missing")

    job.status = JobStatus.running
    job.error = None
    db.commit()

    owns_graph = graph is None
    graph = graph or GraphStore(settings)
    vector_store = vector_store or VectorStore(settings)

    try:
        meeting = db.get(Meeting, job.meeting_id)
        if not meeting:
            raise ValueError("Meeting not found")

        transcript = meeting.transcript
        entities = extract_entities(transcript)
        summary_lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()][:5]
        summary = " ".join(summary_lines)[:800] or transcript[:800]
        meeting.summary = summary
        meeting.artifacts = {
            "decisions": entities["decisions"],
            "tasks": entities["tasks"],
            "risks": [],
            "open_questions": [],
            "referenced_documents": [],
        }

        chunks = chunk_text(transcript)
        embedder = get_embedder(settings)
        vectors = embedder.embed(chunks) if chunks else []

        graph.upsert_node("Meeting", str(meeting.id), {"title": meeting.title})
        if meeting.project_id:
            graph.upsert_node(
                "Project",
                str(meeting.project_id),
                {"name": str(meeting.project_id)},
            )
            graph.upsert_edge(
                "Meeting",
                str(meeting.id),
                "Project",
                str(meeting.project_id),
                "BELONGS_TO",
            )

        for idx, decision_text in enumerate(entities["decisions"]):
            did = f"decision:{meeting.id}:{idx}"
            graph.upsert_node("Decision", did, {"title": decision_text[:200]})
            graph.upsert_edge("Decision", did, "Meeting", str(meeting.id), "DISCUSSED_IN")

        for idx, task_text in enumerate(entities["tasks"]):
            tid = f"task:{meeting.id}:{idx}"
            graph.upsert_node("Task", tid, {"title": task_text[:200]})
            graph.upsert_edge("Task", tid, "Meeting", str(meeting.id), "DISCUSSED_IN")

        for idx, (chunk, vector) in enumerate(zip(chunks, vectors)):
            point_id = str(uuid.uuid5(meeting.id, f"meeting-chunk-{idx}"))
            vector_store.upsert(
                point_id=point_id,
                vector=vector,
                payload={
                    "meeting_id": str(meeting.id),
                    "title": meeting.title,
                    "snippet": chunk[:400],
                    "project_id": str(meeting.project_id) if meeting.project_id else None,
                    "visibility": "org",
                    "type": "meeting",
                },
            )

        job.status = JobStatus.completed
        job.stats = {
            "chunks_indexed": len(chunks),
            "decisions": len(entities["decisions"]),
            "tasks": len(entities["tasks"]),
        }
        db.commit()
        db.refresh(job)
        return job
    except Exception as exc:
        job.status = JobStatus.failed
        job.error = str(exc)
        db.commit()
        db.refresh(job)
        return job
    finally:
        if owns_graph:
            try:
                graph.close()
            except Exception:
                pass
