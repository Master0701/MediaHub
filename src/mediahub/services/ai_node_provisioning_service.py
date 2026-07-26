"""Zentrale Bereitstellung und Prüfung des optionalen MediaHub-AI-Nodes."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from src.mediahub.services.ai_node_ssh_setup_service import (
    AINodeSSHSetupError,
    AINodeSSHSetupService,
)


class AINodeProvisioningError(RuntimeError):
    """Die Prüfung oder Bereitstellung des AI-Nodes ist fehlgeschlagen."""


class AINodeInstallationState(StrEnum):
    READY = "ready"
    TOKEN_MISSING = "token_missing"
    SERVICE_STOPPED = "service_stopped"
    SOFTWARE_MISSING = "software_missing"
    SSH_UNREACHABLE = "ssh_unreachable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class AINodeProvisioningStatus:
    state: AINodeInstallationState
    ssh_reachable: bool
    software_installed: bool
    service_active: bool
    token_configured: bool
    project_dir: str
    service_name: str
    message: str


@dataclass(frozen=True, slots=True)
class AINodeProvisioningResult:
    status: AINodeProvisioningStatus
    api_token: str = ""
    changed: bool = False


class AINodeProvisioningService:
    DEFAULT_PROJECT_DIR = "/opt/mediahub/ai-node"
    DEFAULT_SERVICE_NAME = "mediahub-ai-node"
    DEFAULT_REPOSITORY_URL = (
        "https://github.com/Master0701/MediaHub-AI-Node.git"
    )
    TOKEN_ENV_NAME = "MEDIAHUB_AI_NODE_API_TOKEN"

    def __init__(
        self,
        *,
        host: str,
        ssh_port: int = 22,
        username: str = "mediahub",
        password: str,
        project_dir: str = DEFAULT_PROJECT_DIR,
        service_name: str = DEFAULT_SERVICE_NAME,
        repository_url: str = DEFAULT_REPOSITORY_URL,
        timeout: float = 15.0,
    ) -> None:
        self.host = str(host).strip()
        self.ssh_port = int(ssh_port)
        self.username = str(username).strip() or "mediahub"
        self.password = str(password)
        self.project_dir = str(project_dir).strip() or self.DEFAULT_PROJECT_DIR
        self.service_name = str(service_name).strip() or self.DEFAULT_SERVICE_NAME
        self.repository_url = (
            str(repository_url).strip() or self.DEFAULT_REPOSITORY_URL
        )
        self.timeout = float(timeout)

    def inspect(self) -> AINodeProvisioningStatus:
        self._validate_connection_data()
        client = self._connect()
        try:
            software_installed = self._run(
                client,
                f"test -f {self._quote(self.project_dir)}/app/main.py "
                "&& echo yes || echo no",
            ).strip() == "yes"

            service_active = self._run(
                client,
                f"systemctl is-active {self._quote(self.service_name)} "
                "2>/dev/null || true",
            ).strip() == "active"

            env_file = f"{self.project_dir}/.env"
            token_configured = self._sudo(
                client,
                f"test -f {self._quote(env_file)} && "
                f"grep -Eq '^{self.TOKEN_ENV_NAME}=.{{32,}}$' "
                f"{self._quote(env_file)} "
                "&& echo yes || echo no",
            ).strip() == "yes"

            if not software_installed:
                state = AINodeInstallationState.SOFTWARE_MISSING
                message = "MediaHub-AI-Node ist noch nicht installiert."
            elif not service_active:
                state = AINodeInstallationState.SERVICE_STOPPED
                message = "AI-Node ist installiert, aber der Dienst läuft nicht."
            elif not token_configured:
                state = AINodeInstallationState.TOKEN_MISSING
                message = "AI-Node läuft, aber das API-Token fehlt."
            else:
                state = AINodeInstallationState.READY
                message = "AI-Node ist installiert und bereit."

            return AINodeProvisioningStatus(
                state=state,
                ssh_reachable=True,
                software_installed=software_installed,
                service_active=service_active,
                token_configured=token_configured,
                project_dir=self.project_dir,
                service_name=self.service_name,
                message=message,
            )
        finally:
            client.close()

    def ensure_ready(self) -> AINodeProvisioningResult:
        status = self.inspect()

        if status.state is AINodeInstallationState.SOFTWARE_MISSING:
            return self.install_node()

        if status.state is AINodeInstallationState.SERVICE_STOPPED:
            repaired = self.repair_service()
            if repaired.status.state is AINodeInstallationState.TOKEN_MISSING:
                return self.ensure_token()
            return repaired

        if status.state is AINodeInstallationState.TOKEN_MISSING:
            return self.ensure_token()

        return AINodeProvisioningResult(
            status=status,
            api_token=self._read_remote_token(),
            changed=False,
        )

    def repair_service(self) -> AINodeProvisioningResult:
        client = self._connect()
        try:
            self._sudo(client, "systemctl daemon-reload")
            self._sudo(
                client,
                f"systemctl restart {self._quote(self.service_name)}",
            )
        finally:
            client.close()

        self._wait_for_service()
        status = self.inspect()

        return AINodeProvisioningResult(
            status=status,
            api_token=self._read_remote_token(),
            changed=True,
        )

    def install_node(self) -> AINodeProvisioningResult:
        client = self._connect()
        temp_dir = "/tmp/mediahub-ai-node-install"
        output = ""

        try:
            self._sudo(
                client,
                "apt-get update && "
                "DEBIAN_FRONTEND=noninteractive apt-get install -y "
                "git ca-certificates",
                timeout=600.0,
            )
            self._run(
                client,
                f"rm -rf {self._quote(temp_dir)} && "
                f"git clone --depth 1 {self._quote(self.repository_url)} "
                f"{self._quote(temp_dir)}",
                timeout=180.0,
            )
            command = (
                f"cd {self._quote(temp_dir)} && "
                "MEDIAHUB_NONINTERACTIVE=1 "
                f"MEDIAHUB_USER={self._quote(self.username)} "
                f"PROJECT_DIR={self._quote(self.project_dir)} "
                f"SERVICE_NAME={self._quote(self.service_name)} "
                "bash ./install.sh"
            )
            output = self._sudo(
                client,
                command,
                timeout=1800.0,
            )
        finally:
            try:
                self._run(
                    client,
                    f"rm -rf {self._quote(temp_dir)}",
                )
            except Exception:
                pass
            client.close()

        # Die .env auf dem Zielsystem ist die verbindliche Tokenquelle.
        token = self._read_remote_token()

        self._wait_for_service()
        status = self.inspect()

        if status.state is not AINodeInstallationState.READY:
            raise AINodeProvisioningError(
                "Die Installation wurde ausgeführt, "
                f"aber der AI-Node ist nicht bereit: {status.message}"
            )

        return AINodeProvisioningResult(
            status=status,
            api_token=token,
            changed=True,
        )

    def ensure_token(self) -> AINodeProvisioningResult:
        status = self.inspect()

        if status.state is AINodeInstallationState.SOFTWARE_MISSING:
            raise AINodeProvisioningError(
                "Der AI-Node ist noch nicht installiert."
            )

        try:
            setup = AINodeSSHSetupService(
                host=self.host,
                port=self.ssh_port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
            )
            result = setup.configure()
        except AINodeSSHSetupError as exc:
            raise AINodeProvisioningError(str(exc)) from exc

        updated_status = AINodeProvisioningStatus(
            state=AINodeInstallationState.READY,
            ssh_reachable=True,
            software_installed=True,
            service_active=True,
            token_configured=result.token_in_process,
            project_dir=self.project_dir,
            service_name=self.service_name,
            message="API-Token wurde eingerichtet und der Dienst neu gestartet.",
        )

        return AINodeProvisioningResult(
            status=updated_status,
            api_token=result.api_token,
            changed=True,
        )

    def _read_remote_token(self) -> str:
        """Liest und validiert das Token aus der geschützten .env."""

        client = self._connect()
        try:
            env_file = f"{self.project_dir}/.env"
            command = (
                f"sed -n "
                f"'s/^{self.TOKEN_ENV_NAME}=//p' "
                f"{self._quote(env_file)} | tail -n 1"
            )
            token = self._sudo(
                client,
                command,
            ).strip()

            if len(token) < 32:
                raise AINodeProvisioningError(
                    "Die Installation war erfolgreich, aber das "
                    "API-Token in der entfernten .env ist leer "
                    "oder ungültig."
                )

            return token
        finally:
            client.close()

    def _wait_for_service(self) -> None:
        client = self._connect()
        try:
            for _attempt in range(40):
                output = self._run(
                    client,
                    f"systemctl is-active {self._quote(self.service_name)} "
                    "2>/dev/null || true",
                )
                if output.strip() == "active":
                    return
                time.sleep(0.5)
        finally:
            client.close()

        raise AINodeProvisioningError(
            "Der AI-Node-Dienst wurde nicht rechtzeitig aktiv."
        )

    def _validate_connection_data(self) -> None:
        if not self.host:
            raise AINodeProvisioningError("Keine AI-Node-Adresse angegeben.")
        if not self.username:
            raise AINodeProvisioningError("Kein SSH-Benutzer angegeben.")
        if not self.password:
            raise AINodeProvisioningError(
                "Für die SSH-Prüfung wird das Passwort benötigt."
            )

    def _connect(self) -> Any:
        try:
            import paramiko
        except ImportError as exc:
            raise AINodeProvisioningError(
                "Paramiko fehlt. Bitte die MediaHub-Abhängigkeiten "
                "vollständig installieren."
            ) from exc

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            client.connect(
                hostname=self.host,
                port=self.ssh_port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                auth_timeout=self.timeout,
                banner_timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )
        except Exception as exc:
            client.close()
            raise AINodeProvisioningError(
                f"SSH-Verbindung fehlgeschlagen: {exc}"
            ) from exc

        return client

    def _sudo(
        self,
        client: Any,
        command: str,
        *,
        timeout: float | None = None,
    ) -> str:
        stdin, stdout, stderr = client.exec_command(
            f"sudo -S -p '' sh -lc {self._quote(command)}",
            timeout=timeout or self.timeout,
        )
        stdin.write(self.password + "\n")
        stdin.flush()

        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")

        if exit_status != 0:
            raise AINodeProvisioningError(
                error.strip()
                or output.strip()
                or f"sudo-Befehl fehlgeschlagen: {command}"
            )
        return output

    def _run(
        self,
        client: Any,
        command: str,
        *,
        timeout: float | None = None,
    ) -> str:
        _stdin, stdout, stderr = client.exec_command(
            command,
            timeout=timeout or self.timeout,
        )
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")

        if exit_status != 0:
            raise AINodeProvisioningError(
                error.strip()
                or output.strip()
                or f"SSH-Befehl fehlgeschlagen: {command}"
            )
        return output

    @staticmethod
    def _parse_installer_value(output: str, key: str) -> str:
        match = re.search(
            rf"(?m)^{re.escape(key)}=(.+)$",
            str(output),
        )
        return match.group(1).strip() if match else ""

    @staticmethod
    def _quote(value: str) -> str:
        return "'" + str(value).replace("'", "'\\''") + "'"
