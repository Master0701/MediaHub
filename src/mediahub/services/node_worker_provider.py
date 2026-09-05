from __future__ import annotations

from pathlib import Path
from typing import Any

from src.mediahub.services.ai_node_service import (
    AINodeConnectionError,
    AINodeService,
)
from src.mediahub.services.compute_node_service import (
    ComputeNodeConnectionError,
    ComputeNodeService,
)
from src.mediahub.services.settings_service import SettingsService


class NodeWorkerProvider:
    """Zentraler Dispatcher für ausführbare Node-Worker."""

    def __init__(self, base_dir: str | Path) -> None:
        self.base_dir = Path(base_dir)
        self.settings_service = SettingsService(self.base_dir)
        self.compute_service = ComputeNodeService(
            self.settings_service
        )

    def supports(
        self,
        capability: str,
    ) -> bool:
        return bool(
            self.available_workers(capability)
        )

    def available_workers(
        self,
        capability: str,
    ) -> list[dict[str, Any]]:
        wanted = str(capability or "").strip()

        if not wanted:
            return []

        workers: list[dict[str, Any]] = []

        workers.extend(
            self._windows_compute_workers(
                wanted
            )
        )

        pi = self._ai_node_worker(
            wanted
        )

        if pi is not None:
            workers.append(pi)

        return workers

    def execute(
        self,
        capability: str,
        input_path: str | Path,
        *,
        payload: dict[str, Any] | None = None,
        preferred_node_id: str | None = None,
    ) -> dict[str, Any]:
        source = Path(input_path)

        if not source.is_file():
            raise FileNotFoundError(source)

        workers = self.available_workers(
            capability
        )

        if preferred_node_id:
            wanted = str(
                preferred_node_id
            ).strip()

            workers.sort(
                key=lambda item: (
                    item.get("node_id") != wanted
                )
            )

        if not workers:
            raise RuntimeError(
                f"Keine verfügbare Node-Capability "
                f"für '{capability}'."
            )

        errors: list[str] = []

        for worker in workers:
            try:
                if (
                    worker.get("node_type")
                    == "windows_compute"
                ):
                    return self._execute_windows_compute(
                        worker,
                        capability,
                        source,
                        payload or {},
                    )

                if (
                    worker.get("node_type")
                    == "raspberry_pi"
                ):
                    return self._execute_ai_node(
                        worker,
                        capability,
                        source,
                        payload or {},
                    )

            except (
                ComputeNodeConnectionError,
                AINodeConnectionError,
                RuntimeError,
                OSError,
            ) as error:
                errors.append(
                    f"{worker.get('name')}: {error}"
                )

        raise RuntimeError(
            "Keine Node konnte den Auftrag "
            "erfolgreich ausführen. "
            + " | ".join(errors)
        )

    def _windows_compute_workers(
        self,
        capability: str,
    ) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []

        for node in self.compute_service.enabled_nodes():
            try:
                client = self.compute_service.client_for(
                    node,
                    timeout=5.0,
                )

                health = client.health()

                if not health.online:
                    continue

                workers = client.workers()

                matched = [
                    item
                    for item in workers
                    if self._worker_supports(
                        item,
                        capability,
                    )
                ]

                if not matched:
                    continue

                result.append(
                    {
                        "node_id": node.node_id,
                        "name": (
                            node.name
                            or node.node_id
                        ),
                        "node_type": "windows_compute",
                        "client": client,
                        "workers": matched,
                        "priority": 10,
                    }
                )

            except (
                ComputeNodeConnectionError,
                OSError,
            ):
                continue

        return sorted(
            result,
            key=lambda item: int(
                item.get("priority", 100)
            ),
        )

    def _ai_node_worker(
        self,
        capability: str,
    ) -> dict[str, Any] | None:
        settings = self.settings_service.load()

        if not isinstance(settings, dict):
            return None

        service = AINodeService.from_settings(
            settings,
            timeout=5.0,
        )

        health = service.health()

        if not health.online:
            return None

        try:
            job_types = service.list_job_types()
        except AINodeConnectionError:
            return None

        if capability not in job_types:
            return None

        return {
            "node_id": "ai_node",
            "name": "Raspberry-Pi-AI-Node",
            "node_type": "raspberry_pi",
            "client": service,
            "priority": 20,
        }

    @staticmethod
    def _worker_supports(
        worker: dict[str, Any],
        capability: str,
    ) -> bool:
        job_types = worker.get("job_types")

        if isinstance(job_types, list):
            return capability in {
                str(value).strip()
                for value in job_types
            }

        job_type = str(
            worker.get("job_type")
            or ""
        ).strip()

        return job_type == capability

    @staticmethod
    def _normalized_output(
        job: dict[str, Any],
    ) -> dict[str, Any]:
        result = job.get("result")

        if not isinstance(result, dict):
            return {}

        nested = result.get("output")

        if isinstance(nested, dict):
            return nested

        return result

    def _execute_windows_compute(
        self,
        worker: dict[str, Any],
        capability: str,
        source: Path,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        client = worker["client"]

        job = client.create_job(
            capability,
            payload=payload,
        )

        job_id = str(
            job.get("id")
            or job.get("job_id")
            or ""
        ).strip()

        if not job_id:
            raise RuntimeError(
                "Windows Compute Node "
                "lieferte keine Job-ID."
            )

        client.upload_job_input(
            job_id,
            source,
        )

        result = client.execute_job_and_wait(
            job_id,
        )

        return {
            "provider": "node_worker",
            "node_id": worker["node_id"],
            "node_name": worker["name"],
            "node_type": worker["node_type"],
            "capability": capability,
            "job": result,
            "output": self._normalized_output(result),
        }

    def _execute_ai_node(
        self,
        worker: dict[str, Any],
        capability: str,
        source: Path,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        service = worker["client"]

        job = service.create_job(
            capability,
            payload,
            preparing=True,
        )

        job_id = int(job["id"])

        service.upload_job_input(
            job_id,
            source,
        )

        result = service.wait_for_job(
            job_id,
        )

        return {
            "provider": "node_worker",
            "node_id": worker["node_id"],
            "node_name": worker["name"],
            "node_type": worker["node_type"],
            "capability": capability,
            "job": result,
            "output": self._normalized_output(result),
        }
