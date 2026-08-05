from io import BytesIO
from unittest.mock import MagicMock, patch


def test_create_project(client, auth_headers):
    res = client.post(
        "/v1/projects",
        headers=auth_headers,
        json={"name": "Phoenix", "description": "Pilot"},
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["name"] == "Phoenix"

    listed = client.get("/v1/projects", headers=auth_headers)
    assert listed.status_code == 200
    assert any(p["name"] == "Phoenix" for p in listed.json())


def test_upload_document_with_mocks(client, auth_headers):
    fake_graph = MagicMock()
    fake_vector = MagicMock()

    with (
        patch("app.api.routes.documents.ObjectStorage") as storage_cls,
        patch("app.api.routes.documents.process_document_job") as process_job,
    ):
        storage_cls.return_value.put_bytes.side_effect = Exception("no minio")
        process_job.side_effect = lambda db, settings, job_id: None

        res = client.post(
            "/v1/documents",
            headers=auth_headers,
            files={"file": ("note.txt", BytesIO(b"Project Phoenix notes"), "text/plain")},
            data={"title": "Notes"},
        )
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["document"]["title"] == "Notes"
        assert "job_id" in body
        process_job.assert_called_once()
