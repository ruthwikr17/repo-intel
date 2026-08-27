import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock, AsyncMock
from app.main import app


@pytest.mark.asyncio
async def test_health_still_works():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_trigger_analysis_invalid_url():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/repos/analyze", json={"url": "https://gitlab.com/user/repo"}
        )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_trigger_analysis_valid_url():
    mock_task = MagicMock()
    mock_task.id = "test-task-123"

    with patch("app.routes.repos.run_full_analysis") as mock_fn:
        mock_fn.delay.return_value = mock_task
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/repos/analyze", json={"url": "https://github.com/psf/requests"}
            )
    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["task_id"] == "test-task-123"
    assert data["status"] == "queued"


@pytest.mark.asyncio
async def test_get_analysis_status_pending():
    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_result.info = None

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_get_analysis_status_completed():
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.result = {"status": "completed", "analysis_id": 1}

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["result"]["analysis_id"] == 1


@pytest.mark.asyncio
async def test_get_analysis_status_failed():
    mock_result = MagicMock()
    mock_result.state = "FAILURE"
    mock_result.info = "Task failed"

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert data["error"] == "Task failed"


@pytest.mark.asyncio
async def test_get_analysis_status_processing():
    mock_result = MagicMock()
    mock_result.state = "PROGRESS"
    mock_result.info = {"step": "Running AI analysis"}

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert data["step"] == "Running AI analysis"


@pytest.mark.asyncio
async def test_get_analysis_status_started():
    mock_result = MagicMock()
    mock_result.state = "STARTED"
    mock_result.info = {"step": "Fetching GitHub data"}

    with patch("app.routes.repos.AsyncResult", return_value=mock_result):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/repos/analyze/status/fake-task-id")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["step"] == "Fetching GitHub data"
