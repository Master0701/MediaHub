from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.mediahub.services.compute_node_service import (
    ComputeNodeClient,
    ComputeNodeConfig,
    ComputeNodeConnectionError,
)


def make_client() -> ComputeNodeClient:
    config = ComputeNodeConfig(
        node_id="test-node",
        name="Test Compute Node",
        node_type="windows_compute",
        host="127.0.0.1",
        api_port=8766,
        api_token="test-token",
        enabled=True,
    )
    return ComputeNodeClient(
        config,
        timeout=5.0,
    )


def test_jobs_requests_job_list():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "jobs": [
                {
                    "job_id": "job-1",
                    "status": "queued",
                }
            ]
        }
    )

    result = client.jobs()

    assert result == [
        {
            "job_id": "job-1",
            "status": "queued",
        }
    ]
    client._request_json.assert_called_once_with(
        "GET",
        "/jobs",
    )


def test_jobs_rejects_invalid_job_list():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "jobs": "invalid",
        }
    )

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-Liste",
    ):
        client.jobs()


def test_job_requests_specific_job():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "job_id": "job-1",
            "status": "completed",
        }
    )

    result = client.job(" job-1 ")

    assert result["job_id"] == "job-1"
    client._request_json.assert_called_once_with(
        "GET",
        "/jobs/job-1",
    )


def test_job_rejects_empty_id():
    client = make_client()

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-ID fehlt",
    ):
        client.job("   ")


def test_create_job_sends_payload_and_execution():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "job_id": "speech-1",
            "status": "queued",
        }
    )

    result = client.create_job(
        " speech_to_text ",
        payload={
            "input": r"D:\video\test.avi",
        },
        execution={
            "mode": "auto",
            "cpu_threads": 4,
        },
    )

    assert result["job_id"] == "speech-1"

    client._request_json.assert_called_once_with(
        "POST",
        "/jobs",
        payload={
            "job_type": "speech_to_text",
            "payload": {
                "input": r"D:\video\test.avi",
            },
            "execution": {
                "mode": "auto",
                "cpu_threads": 4,
            },
        },
    )


def test_create_job_defaults_to_empty_dicts():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "job_id": "job-1",
        }
    )

    client.create_job("test_job")

    client._request_json.assert_called_once_with(
        "POST",
        "/jobs",
        payload={
            "job_type": "test_job",
            "payload": {},
            "execution": {},
        },
    )


@pytest.mark.parametrize(
    "job_type",
    [
        "",
        "   ",
    ],
)
def test_create_job_rejects_empty_type(job_type):
    client = make_client()

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-Typ fehlt",
    ):
        client.create_job(job_type)


def test_create_job_rejects_invalid_payload():
    client = make_client()

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-Payload",
    ):
        client.create_job(
            "test_job",
            payload=["invalid"],
        )


def test_create_job_rejects_invalid_execution():
    client = make_client()

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-Ausführung",
    ):
        client.create_job(
            "test_job",
            execution=["invalid"],
        )


def test_execute_job_requests_execute_endpoint():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "job_id": "job-1",
            "status": "completed",
        }
    )

    result = client.execute_job(" job-1 ")

    assert result["status"] == "completed"
    client._request_json.assert_called_once_with(
        "POST",
        "/jobs/job-1/execute",
    )


def test_execute_job_rejects_empty_id():
    client = make_client()

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-ID fehlt",
    ):
        client.execute_job("")


def test_cancel_job_requests_delete_endpoint():
    client = make_client()
    client._request_json = MagicMock(
        return_value={
            "job_id": "job-1",
            "status": "cancelled",
        }
    )

    result = client.cancel_job(" job-1 ")

    assert result["status"] == "cancelled"
    client._request_json.assert_called_once_with(
        "DELETE",
        "/jobs/job-1",
    )


def test_cancel_job_rejects_empty_id():
    client = make_client()

    with pytest.raises(
        ComputeNodeConnectionError,
        match="Job-ID fehlt",
    ):
        client.cancel_job(" ")
