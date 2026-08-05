from app.services.embeddings import HashEmbedder


def test_hash_embedder_deterministic():
    emb = HashEmbedder(dim=64)
    a = emb.embed(["Project Phoenix decision"])[0]
    b = emb.embed(["Project Phoenix decision"])[0]
    assert a == b
    assert len(a) == 64
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6
