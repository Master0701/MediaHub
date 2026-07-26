from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVICE_DIR = ROOT / "src/mediahub/services"
GUI_FILE = ROOT / "src/mediahub/gui/global_settings_panel.py"

if not SERVICE_DIR.is_dir() or not GUI_FILE.is_file():
    raise SystemExit("Das Skript muss im MediaHub-Hauptordner ausgeführt werden.")

ssh_service = '''"""Einmalige Einrichtung des AI-Node-API-Tokens per SSH."""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass


class AINodeSSHSetupError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class AINodeSSHSetupResult:
    api_token: str
    token_in_process: bool


class AINodeSSHSetupService:
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
        self.host = host.strip()
        self.port = int(port)
        self.username = username.strip()
        self.password = password
        self.timeout = timeout

    def configure(self) -> AINodeSSHSetupResult:
        if not self.host:
            raise AINodeSSHSetupError("Keine AI-Node-Adresse angegeben.")
        if not self.username:
            raise AINodeSSHSetupError("Kein SSH-Benutzer angegeben.")
        if not self.password:
            raise AINodeSSHSetupError("SSH-Passwort fehlt.")

        try:
            import paramiko
        except ImportError as exc:
            raise AINodeSSHSetupError(
                "Paramiko fehlt. Bitte 'python -m pip install paramiko' ausführen."
            ) from exc

        token = secrets.token_urlsafe(48)
        override = (
            "[Service]\n"
            'Environment="PATH=/opt/mediahub/venv/bin:/usr/local/sbin:'
            '/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
            f'Environment="{self.TOKEN_ENV_NAME}={token}"\n'
        )

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

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
                "mkdir -p /etc/systemd/system/"
                "mediahub-ai-node.service.d",
            )
            self._sudo(
                client,
                f"install -m 600 {temp_path} {self.OVERRIDE_PATH}",
            )
            self._sudo(client, f"rm -f {temp_path}")
            self._sudo(client, "systemctl daemon-reload")
            self._sudo(
                client,
                f"systemctl restart {self.SERVICE_NAME}",
            )

            for _ in range(12):
                time.sleep(0.5)
                output = self._run(
                    client,
                    "PID=$(systemctl show -p MainPID --value "
                    f"{self.SERVICE_NAME}); "
                    'if [ -n "$PID" ] && [ -r "/proc/$PID/environ" ]; then '
                    "tr '\\0' '\\n' < /proc/$PID/environ | "
                    f"grep -q '^{self.TOKEN_ENV_NAME}=' && echo yes || echo no; "
                    "else echo no; fi",
                )
                if output.strip() == "yes":
                    return AINodeSSHSetupResult(
                        api_token=token,
                        token_in_process=True,
                    )

            raise AINodeSSHSetupError(
                "Token wurde geschrieben, ist aber nicht im laufenden Prozess."
            )
        except AINodeSSHSetupError:
            raise
        except Exception as exc:
            raise AINodeSSHSetupError(
                f"SSH-Einrichtung fehlgeschlagen: {exc}"
            ) from exc
        finally:
            client.close()

    def _sudo(self, client, command: str) -> str:
        stdin, stdout, stderr = client.exec_command(
            f"sudo -S -p '' {command}",
            timeout=self.timeout,
        )
        stdin.write(self.password + "\n")
        stdin.flush()
        status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        if status != 0:
            raise AINodeSSHSetupError(
                error.strip() or output.strip() or command
            )
        return output

    def _run(self, client, command: str) -> str:
        _stdin, stdout, stderr = client.exec_command(
            command,
            timeout=self.timeout,
        )
        status = stdout.channel.recv_exit_status()
        output = stdout.read().decode("utf-8", errors="replace")
        error = stderr.read().decode("utf-8", errors="replace")
        if status != 0:
            raise AINodeSSHSetupError(
                error.strip() or output.strip() or command
            )
        return output
'''

service_file = SERVICE_DIR / "ai_node_ssh_setup_service.py"
service_file.write_text(ssh_service, encoding="utf-8", newline="\n")
print(f"Erstellt: {service_file}")

gui = GUI_FILE.read_text(encoding="utf-8")

marker = "from src.mediahub.services.ai_node_service import AINodeService\n"
imports = (
    marker
    + "from src.mediahub.services.ai_node_ssh_setup_service import (\n"
    + "    AINodeSSHSetupError,\n"
    + "    AINodeSSHSetupService,\n"
    + ")\n"
)
if "ai_node_ssh_setup_service" not in gui:
    if marker not in gui:
        raise SystemExit("AINodeService-Import wurde nicht gefunden.")
    gui = gui.replace(marker, imports, 1)

gui = gui.replace(
    'QPushButton("AI-Node-Verbindung testen")',
    'QPushButton("AI-Node einrichten / Verbindung prüfen")',
    1,
)

start = gui.find("    def test_ai_node_connection(self):\n")
if start < 0:
    raise SystemExit("test_ai_node_connection wurde nicht gefunden.")
end = gui.find("\n    def ", start + 10)
if end < 0:
    raise SystemExit("Methodenende wurde nicht gefunden.")

new_method = '''    def test_ai_node_connection(self):
        self.btn_test_ai_node.setEnabled(False)
        self.ai_connection_status.setText("Verbindung wird geprüft ...")

        host = self.ai_node_host.text().strip()
        ssh_password = self.ai_ssh_password.text()

        try:
            if not self.ai_node_enabled.isChecked():
                self.ai_connection_status.setText(
                    "Der Raspberry-Pi-AI-Node ist deaktiviert."
                )
                return

            if not host:
                self.ai_connection_status.setText(
                    "Bitte zuerst die AI-Node-Adresse eintragen."
                )
                return

            token = self.ai_node_api_token.text().strip()

            if not token:
                if not ssh_password:
                    self.ai_connection_status.setText(
                        "Kein API-Token vorhanden. Bitte einmalig das "
                        "SSH-Passwort eintragen und erneut prüfen."
                    )
                    return

                self.ai_connection_status.setText(
                    "API-Token wird einmalig über SSH eingerichtet ..."
                )

                setup = AINodeSSHSetupService(
                    host=host,
                    port=self.ai_ssh_port.value(),
                    username=(
                        self.ai_ssh_username.text().strip()
                        or "mediahub"
                    ),
                    password=ssh_password,
                )
                result = setup.configure()
                token = result.api_token
                self.ai_node_api_token.setText(token)

                data = self.settings_service.load()
                if not isinstance(data, dict):
                    data = {}
                ai = data.get("ai")
                if not isinstance(ai, dict):
                    ai = {}
                ai.update(
                    {
                        "node_enabled": True,
                        "node_host": host,
                        "api_port": self.ai_node_api_port.value(),
                        "api_token": token,
                        "ssh_port": self.ai_ssh_port.value(),
                        "ssh_username": (
                            self.ai_ssh_username.text().strip()
                            or "mediahub"
                        ),
                        "install_path": (
                            self.ai_install_path.text().strip()
                            or "/opt/mediahub/ai-node"
                        ),
                        "mode": self.ai_mode.currentText(),
                    }
                )
                data["ai"] = ai
                self.settings_service.save(data)

            settings = {
                "ai": {
                    "node_enabled": True,
                    "node_host": host,
                    "api_port": self.ai_node_api_port.value(),
                    "api_token": token,
                    "ssh_port": self.ai_ssh_port.value(),
                    "ssh_username": (
                        self.ai_ssh_username.text().strip()
                        or "mediahub"
                    ),
                    "install_path": (
                        self.ai_install_path.text().strip()
                        or "/opt/mediahub/ai-node"
                    ),
                }
            }

            service = AINodeService.from_settings(
                settings,
                timeout=8.0,
            )
            health = service.health()

            if not health.online:
                self.ai_connection_status.setText(
                    f"Keine Verbindung zum AI-Node: {health.message}"
                )
                return

            plugins = service.list_plugins()
            detected = (
                health.detected_plugins
                if health.detected_plugins is not None
                else len(plugins)
            )
            loaded = (
                health.loaded_plugins
                if health.loaded_plugins is not None
                else "?"
            )

            self.ai_connection_status.setText(
                "AI-Node online – "
                f"Version {health.version}; "
                f"{detected} Plugin(s) erkannt, "
                f"{loaded} geladen; "
                "API-Token verfügbar."
            )
        except AINodeSSHSetupError as error:
            self.ai_connection_status.setText(
                f"Automatische Einrichtung fehlgeschlagen: {error}"
            )
        except Exception as error:
            self.ai_connection_status.setText(
                f"Verbindungsprüfung fehlgeschlagen: {error}"
            )
        finally:
            self.ai_ssh_password.clear()
            self.btn_test_ai_node.setEnabled(True)
'''

gui = gui[:start] + new_method + gui[end:]
GUI_FILE.write_text(gui, encoding="utf-8", newline="\n")
print(f"Aktualisiert: {GUI_FILE}")

requirements = ROOT / "requirements.txt"
if requirements.is_file():
    req = requirements.read_text(encoding="utf-8")
    if "paramiko" not in req.lower():
        if req and not req.endswith("\n"):
            req += "\n"
        req += "paramiko>=3.4,<5\n"
        requirements.write_text(req, encoding="utf-8", newline="\n")
        print(f"Aktualisiert: {requirements}")

print("Automatische Token-Einrichtung eingebaut.")
