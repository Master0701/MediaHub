MediaHub Plugin Write-API Fix 5 – korrigierte Version

1. ZIP in den MediaHub-Hauptordner entpacken.
2. PowerShell im MediaHub-Hauptordner öffnen.
3. Ausführen:

   python apply_plugin_write_api_fix5_fixed.py

Der Fix:
- sucht die vollständige MediaHubPluginAPI(...)‑Klammer korrekt,
- erstellt Sicherungen,
- prüft beide geänderten Python-Dateien,
- rollt bei einem Fehler automatisch zurück.

Danach testen:

   python main.py
