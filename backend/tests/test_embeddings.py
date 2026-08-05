from app.services.embeddings import HashEmbedder


def test_hash_embedder_deterministic():
    emb = HashEmbedder(dim=64)
    a = emb.embed(["Project Phoenix decision"])[0]
    b = emb.embed(["Project Phoenix decision"])[0]
    assert a == b
    assert len(a) == 64
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_chunking():
    from app.services.ingest import chunk_text

    chunks = chunk_text("word " * 500, size=100, overlap=20)
    assert len(chunks) > 1
    assert all(chunks)
