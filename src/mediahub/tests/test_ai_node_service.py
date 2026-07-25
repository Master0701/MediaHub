"""Tests für den MediaHub-AI-Node-Verbindungsservice."""

from __future__ import annotations

from src.mediahub.services.ai_node_service import (
    AINodeConnectionConfig,
    AINodeService,
)


def test_config_from_settings() -> None:
    service = AINodeService.from_settings(
        {
            "ai": {
                "node_enabled": True,
                "node_host": "192.168.1.75",
                "api_port": 8765,
                "api_token": "secret",
                "ssh_port": 22,
                "ssh_username": "mediahub",
                "install_path": "/opt/mediahub/ai-node",
            }
        }
    )

    assert service.config.enabled is True
    assert service.config.host == "192.168.1.75"
    assert service.config.base_url == "http://192.168.1.75:8765"


def test_disabled_health() -> None:
    service = AINodeService(AINodeConnectionConfig(enabled=False))

    health = service.health()

    assert health.online is False
    assert health.status == "disabled"


def test_missing_host_health() -> None:
    service = AINodeService(
        AINodeConnectionConfig(enabled=True, host="")
    )

    health = service.health()

    assert health.online is False
    assert health.status == "not_configured"
