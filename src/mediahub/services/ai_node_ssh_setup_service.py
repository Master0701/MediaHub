"""Einmalige Einrichtung des AI-Node-API-Tokens per SSH."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any


class AINodeSSHSetupError(RuntimeError):
    """Die automatische AI-Node-Einrichtung ist fehlgeschlagen."""


@dataclass(frozen=True, slots=True)
class AINodeSSHSetupResult:
    """Ergebnis der automatischen Token-Einrichtung."""

    api_token: str
    token_in_process: bool


class AINodeSSHSetupService:
    """Richtet das API-Token über eine temporäre SSH-Verbindung ein."""

    TOKEN_ENV_NAME = "MEDIAHUB_AI_NODE_API_TOKEN"
    SERVICE_NAME = "mediahub-ai-node"
    OVERRIDE_PATH = (
        "/etc/systemd/system/"
        "mediahub-ai-node.service.d/override.conf"
    )

    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str,
        password: str,
        timeout: float = 15.0,
    ) -> None:
        self.host = str(host).strip()
        self.port = int(port)
        self.username = str(username).strip()
        self.password = str(password)
        self.timeout = float(timeout)

    def configure(self) -> AINodeSSHSetupResult:
        """Erzeugt und installiert einmalig ein neues API-Token."""

        if not self.host:
            raise AINodeSSHSetupError(
                "Keine AI-Node-Adresse angegeben."
            )
        if not self.username:
            raise AINodeSSHSetupError(
                "Kein SSH-Benutzer angegeben."
            )
        if not self.password:
            raise AINodeSSHSetupError(
                "Für die Ersteinrichtung wird das SSH-Passwort benötigt."
            )

        try:
            import paramiko
        except ImportError as exc:
            raise AINodeSSHSetupError(
                "Paramiko fehlt. Bitte einmal "
                "'python -m pip install paramiko' ausführen."
            ) from exc

        token = secrets.token_urlsafe(48)
        override = (
            "[Service]\n"
            'Environment="PATH=/opt/mediahub/venv/bin:'
            '/usr/local/sbin:/usr/local/bin:/usr/sbin:'
            '/usr/bin:/sbin:/bin"\n'
            f'Environment="{self.TOKEN_ENV_NAME}={token}"\n'
        )

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(
            paramiko.AutoAddPolicy()
        )

        try:
            client.connect(
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                timeout=self.timeout,
                auth_timeout=self.timeout,
                banner_timeout=self.timeout,
                look_for_keys=False,
                allow_agent=False,
            )

            temp_path = "/tmp/mediahub-ai-node-override.conf"

            with client.open_sftp() as sftp:
                with sftp.file(temp_path, "w") as handle:
                    handle.write(override)
                sftp.chmod(temp_path, 0o600)

            self._sudo(
                client,
                "mkdir -p "
                "/etc/systemd/system/"
                "mediahub-ai-node.service.d",
            )
            self._sudo(
                client,
                f"install -m 600 {temp_path} "
                f"{self.OVERRIDE_PATH}",
            )
            self._sudo(
                client,
                f"rm -f {temp_path}",
            )
            self._sudo(
                client,
                "systemctl daemon-reload",
            )
            self._sudo(
                client,
                f"systemctl restart {self.SERVICE_NAME}",
            )

            for _attempt in range(20):
                time.sleep(0.5)
                output = self._run(
                    client,
                    "PID=$(systemctl show -p MainPID --value "
                    f"{self.SERVICE_NAME}); "
                    'if [ -n "$PID" ] && '
                    '[ -r "/proc/$PID/environ" ]; then '
                    "tr '\\0' '\\n' < /proc/$PID/environ | "
                    f"grep -q '^{self.TOKEN_ENV_NAME}=' "
                    "&& echo yes || echo no; "
                    "else echo no; fi",
                )
                if output.strip() == "yes":
                    return AINodeSSHSetupResult(
                        api_token=token,
                        token_in_process=True,
                    )

            raise AINodeSSHSetupError(
                "Das Token wurde geschrieben, ist aber nicht im "
                "laufenden AI-Node-Prozess angekommen."
            )
        except AINodeSSHSetupError:
            raise
        except Exception as exc:
            raise AINodeSSHSetupError(
                f"SSH-Einrichtung fehlgeschlagen: {exc}"
            ) from exc
        finally:
            client.close()

    def _sudo(
        self,
        client: Any,
        command: str,
    ) -> str:
        """Führt einen einzelnen Befehl über sudo aus."""

        stdin, stdout, stderr = client.exec_command(
            f"sudo -S -p '' {command}",
            timeout=self.timeout,
        )
        stdin.write(self.password + "\n")
        stdin.flush()

        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode(
            "utf-8",
            errors="replace",
        )
        error = stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        if exit_status != 0:
            raise AINodeSSHSetupError(
                error.strip()
                or output.strip()
                or f"sudo-Befehl fehlgeschlagen: {command}"
            )

        return output

    def _run(
        self,
        client: Any,
        command: str,
    ) -> str:
        """Führt einen normalen SSH-Befehl aus."""

        _stdin, stdout, stderr = client.exec_command(
            command,
            timeout=self.timeout,
        )
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode(
            "utf-8",
            errors="replace",
        )
        error = stderr.read().decode(
            "utf-8",
            errors="replace",
        )

        if exit_status != 0:
            raise AINodeSSHSetupError(
                error.strip()
                or output.strip()
                or f"SSH-Befehl fehlgeschlagen: {command}"
            )

        return output
