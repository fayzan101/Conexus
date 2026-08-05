from unittest.mock import MagicMock

from app.services.graph import GraphStore


def test_graph_neighbors_with_mock_driver():
    store = GraphStore.__new__(GraphStore)
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = False
    store.driver = driver

    record = {
        "labels": ["Project"],
        "props": {"id": "p1", "name": "Phoenix"},
        "rel": "BELONGS_TO",
    }
    session.run.return_value = [record]

    neighbors = store.neighbors("doc1")
    assert neighbors[0]["id"] == "p1"
    assert neighbors[0]["properties"]["via"] == "BELONGS_TO"


def test_graph_get_node_with_mock_driver():
    store = GraphStore.__new__(GraphStore)
    session = MagicMock()
    driver = MagicMock()
    driver.session.return_value.__enter__.return_value = session
    driver.session.return_value.__exit__.return_value = False
    store.driver = driver

    result = MagicMock()
    result.single.return_value = {"labels": ["Document"], "props": {"id": "doc1", "title": "RFC"}}
    session.run.return_value = result

    node = store.get_node("doc1")
    assert node is not None
    assert node["label"] == "Document"
    assert node["id"] == "doc1"
