from app.services.ingest import chunk_text, extract_entities
from app.services.parsers import extract_text_from_bytes, normalize_whitespace


def test_chunk_text_overlap():
    chunks = chunk_text("word " * 500, size=100, overlap=20)
    assert len(chunks) > 1
    assert all(chunks)


def test_extract_entities():
    text = (
        "Project Phoenix was reviewed by Alice Smith. "
        "Decision: adopt Kubernetes for all services next quarter. "
        "Action item: update the runbook by Friday."
    )
    entities = extract_entities(text)
    assert "Phoenix" in entities["projects"]
    assert "Alice Smith" in entities["people"]
    assert entities["decisions"]
    assert entities["tasks"]


def test_extract_plain_text():
    text = extract_text_from_bytes(b"Hello Enterprise Brain", filename="note.txt")
    assert "Hello Enterprise Brain" in text


def test_normalize_whitespace():
    assert normalize_whitespace("  a\n\nb  ") == "a b"
