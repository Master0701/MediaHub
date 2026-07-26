from pathlib import Path

ROOT = Path(__file__).resolve().parent
service = ROOT / "src/mediahub/services/ai_node_service.py"
panel = ROOT / "src/mediahub/gui/plugin_store_panel.py"

s = service.read_text(encoding="utf-8")
s = s.replace(
    'if path.suffix.lower() != ".zip":',
    'if path.suffix.lower() not in {".zip", ".mhaiplugin"}:'
).replace(
    '"AI-Plugins müssen als ZIP-Paket vorliegen."',
    '"AI-Plugins müssen als .mhaiplugin- oder ZIP-Paket vorliegen."'
)
service.write_text(s, encoding="utf-8", newline="\n")

p = panel.read_text(encoding="utf-8")
p = p.replace(
    '"AI-Plugin-Pakete (*.zip)",',
    '"AI-Plugin-Pakete (*.mhaiplugin *.zip)",'
)
panel.write_text(p, encoding="utf-8", newline="\n")
print("MediaHub akzeptiert jetzt .mhaiplugin und .zip.")
