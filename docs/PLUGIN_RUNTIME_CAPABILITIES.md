# MediaHub Runtime-Capabilities

MediaHub stellt laufenden Plugins eine gemeinsame Capability-Registry über `MediaHubPluginAPI` bereit.

Provider veröffentlichen Fähigkeiten über `get_runtime_capabilities()`. Der `PluginRuntime` registriert sie nach erfolgreichem `start()` und entfernt sie beim Stoppen automatisch. Verbraucher lösen Provider über `resolve_capability()` auf.

Erster End-to-End-Vertrag: `ai.rename_review`.

Sicherheitsgrundsatz: Eine Capability ist nur eine Laufzeit-Schnittstelle. Dateiveränderungen benötigen weiterhin den jeweiligen Vorschau-/Bestätigungs-/Ausführungsweg.
