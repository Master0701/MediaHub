#include "version_generated.iss"

#define YtDlpUrl "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
#define FFmpegUrl1 "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
#define FFmpegUrl2 "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
#define DenoUrl "https://github.com/denoland/deno/releases/latest/download/deno-x86_64-pc-windows-msvc.zip"

[Setup]
AppId={{A8E56F65-5D9B-4B7F-9C20-000000100000}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\MediaHub
DefaultGroupName=MediaHub
OutputDir=..\release
OutputBaseFilename={#MyAppSetupName}
SetupIconFile=..\assets\icons\mediahub.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknüpfung erstellen"; GroupDescription: "Zusätzliche Aufgaben:"; Flags: checkedonce
Name: "downloadtools"; Description: "Benötigte Tools herunterladen"; GroupDescription: "Zusatzkomponenten:"; Flags: checkedonce
Name: "downloadtools\ytdlp"; Description: "yt-dlp herunterladen"; GroupDescription: "Zusatzkomponenten:"; Flags: checkedonce
Name: "downloadtools\ffmpeg"; Description: "FFmpeg, FFprobe und FFplay herunterladen"; GroupDescription: "Zusatzkomponenten:"; Flags: checkedonce
Name: "downloadtools\deno"; Description: "Deno herunterladen"; GroupDescription: "Zusatzkomponenten:"; Flags: checkedonce
Name: "opendocs"; Description: "Schnellstart nach der Installation öffnen"; GroupDescription: "Nach der Installation:"; Flags: checkedonce

[Files]
Source: "..\dist\MediaHub.exe"; DestDir: "{app}"; Flags: ignoreversion

; Dokumentation aus dem Release-Ordner mit installieren.
; build_docs.py / build.py muss diese Dateien vorher erzeugen.
Source: "..\release\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs skipifsourcedoesntexist

; Optional: wichtige Release-Dateien, falls vorhanden.
Source: "..\release\README.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\release\CHANGELOG.txt"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

; MediaHub Wartungs-/Diagnosewerkzeuge
Source: "..\tools\check_mediahub_images.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\tools\rebuild_image_assets.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\tools\migrate_legacy_playlist_images.py"; DestDir: "{app}\tools"; Flags: ignoreversion skipifsourcedoesntexist

[Dirs]
Name: "{app}"; Permissions: users-modify
Name: "{app}\docs"; Permissions: users-modify
Name: "{app}\tools"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\config"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\downloads"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\logs"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\archive"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\cache"; Permissions: users-modify
Name: "{app}\plugins"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\backups"; Permissions: users-modify; Flags: uninsneveruninstall
Name: "{app}\database"; Permissions: users-modify; Flags: uninsneveruninstall

[Icons]
Name: "{group}\MediaHub"; Filename: "{app}\MediaHub.exe"; WorkingDir: "{app}"; IconFilename: "{app}\MediaHub.exe"
Name: "{group}\Schnellstart"; Filename: "{app}\docs\quick\MediaHub_Kurzanleitung.pdf"; WorkingDir: "{app}\docs\quick"; Check: FileExistsEx(ExpandConstant('{app}\docs\quick\MediaHub_Kurzanleitung.pdf'))
Name: "{group}\Benutzerhandbuch"; Filename: "{app}\docs\MediaHub_Handbuch.pdf"; WorkingDir: "{app}\docs"; Check: FileExistsEx(ExpandConstant('{app}\docs\MediaHub_Handbuch.pdf'))
Name: "{group}\Benutzerhandbuch HTML"; Filename: "{app}\docs\MediaHub_Handbuch.html"; WorkingDir: "{app}\docs"; Check: FileExistsEx(ExpandConstant('{app}\docs\MediaHub_Handbuch.html'))
Name: "{group}\Changelog"; Filename: "{app}\CHANGELOG.txt"; WorkingDir: "{app}"; Check: FileExistsEx(ExpandConstant('{app}\CHANGELOG.txt'))
Name: "{group}\Tools-Ordner"; Filename: "{app}\tools"; WorkingDir: "{app}\tools"
Name: "{group}\Deinstallieren"; Filename: "{uninstallexe}"
Name: "{userdesktop}\MediaHub"; Filename: "{app}\MediaHub.exe"; WorkingDir: "{app}"; IconFilename: "{app}\MediaHub.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\MediaHub.exe"; Description: "MediaHub jetzt starten"; WorkingDir: "{app}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\docs\quick\MediaHub_Kurzanleitung.pdf"; Description: "Schnellstart öffnen"; WorkingDir: "{app}\docs\quick"; Flags: postinstall shellexec skipifsilent unchecked; Tasks: opendocs; Check: FileExistsEx(ExpandConstant('{app}\docs\quick\MediaHub_Kurzanleitung.pdf'))


[UninstallRun]
; Falls MediaHub noch läuft, vor dem Entfernen schließen.
Filename: "{cmd}"; Parameters: "/C taskkill /IM MediaHub.exe /F >NUL 2>NUL"; Flags: runhidden

[UninstallDelete]
; Programmdateien entfernen.
Type: files; Name: "{app}\MediaHub.exe"
Type: filesandordirs; Name: "{app}\docs"
Type: files; Name: "{app}\README.txt"
Type: files; Name: "{app}\README.md"
Type: files; Name: "{app}\CHANGELOG.txt"
Type: files; Name: "{app}\CHANGELOG.md"
; Verknüpfungen entfernen.
Type: files; Name: "{userdesktop}\MediaHub.lnk"

[Code]
var
  DeleteDownloads: Boolean;
  DeleteBackups: Boolean;
  DeleteDatabase: Boolean;
  DeleteConfig: Boolean;
  DeleteLogs: Boolean;
  DeletePlugins: Boolean;
  DeleteTools: Boolean;
  DeleteChannelAssets: Boolean;

function FileExistsEx(Path: String): Boolean;
begin
  Result := FileOrDirExists(Path);
end;

function EscapePS(Value: String): String;
begin
  StringChangeEx(Value, '''', '''''', True);
  Result := Value;
end;

function RunPowerShell(ScriptText: String; Title: String): Boolean;
var
  ScriptPath: String;
  ResultCode: Integer;
begin
  Result := False;
  ScriptPath := ExpandConstant('{tmp}\mediahub_setup_task.ps1');

  if not SaveStringToFile(ScriptPath, ScriptText, False) then
  begin
    MsgBox('Das PowerShell-Skript konnte nicht erstellt werden: ' + Title, mbError, MB_OK);
    exit;
  end;

  WizardForm.StatusLabel.Caption := Title;
  WizardForm.ProgressGauge.Style := npbstMarquee;

  if Exec(
    'powershell.exe',
    '-NoProfile -ExecutionPolicy Bypass -File "' + ScriptPath + '"',
    '',
    SW_HIDE,
    ewWaitUntilTerminated,
    ResultCode
  ) then
  begin
    Result := ResultCode = 0;
  end;

  WizardForm.ProgressGauge.Style := npbstNormal;
end;

procedure DownloadYtDlp();
var
  ToolsDir: String;
  Script: String;
begin
  ToolsDir := ExpandConstant('{app}\tools');
  ForceDirectories(ToolsDir);

  if FileExists(ToolsDir + '\yt-dlp.exe') then
  begin
    Log('yt-dlp.exe ist bereits vorhanden.');
    exit;
  end;

  Script :=
    '$ErrorActionPreference = ''Stop''' + #13#10 +
    '$tools = ''' + EscapePS(ToolsDir) + '''' + #13#10 +
    'New-Item -ItemType Directory -Force -Path $tools | Out-Null' + #13#10 +
    'Invoke-WebRequest -UseBasicParsing -Uri ''{#YtDlpUrl}'' -OutFile (Join-Path $tools ''yt-dlp.exe'')' + #13#10;

  if not RunPowerShell(Script, 'yt-dlp wird heruntergeladen ...') then
  begin
    MsgBox(
      'yt-dlp konnte nicht heruntergeladen werden.' + #13#10#13#10 +
      'Die Installation wird trotzdem fortgesetzt.' + #13#10 +
      'Du kannst yt-dlp später im Tool-Center nachinstallieren.',
      mbInformation,
      MB_OK
    );
  end;
end;

function DownloadFFmpegFromUrl(Url: String; SourceName: String): Boolean;
var
  ToolsDir: String;
  Script: String;
begin
  Result := False;
  ToolsDir := ExpandConstant('{app}\tools');
  ForceDirectories(ToolsDir);

  Script :=
    '$ErrorActionPreference = ''Stop''' + #13#10 +
    '$tools = ''' + EscapePS(ToolsDir) + '''' + #13#10 +
    '$url = ''' + EscapePS(Url) + '''' + #13#10 +
    '$zip = Join-Path $env:TEMP ''mediahub_ffmpeg.zip''' + #13#10 +
    '$extract = Join-Path $env:TEMP ''mediahub_ffmpeg_extract''' + #13#10 +
    'New-Item -ItemType Directory -Force -Path $tools | Out-Null' + #13#10 +
    'Remove-Item -Recurse -Force $extract -ErrorAction SilentlyContinue' + #13#10 +
    'Remove-Item -Force $zip -ErrorAction SilentlyContinue' + #13#10 +
    'Invoke-WebRequest -UseBasicParsing -Uri $url -OutFile $zip' + #13#10 +
    'Expand-Archive -Force -Path $zip -DestinationPath $extract' + #13#10 +
    '$ffmpeg = Get-ChildItem -Path $extract -Recurse -Filter ''ffmpeg.exe'' | Select-Object -First 1' + #13#10 +
    '$ffprobe = Get-ChildItem -Path $extract -Recurse -Filter ''ffprobe.exe'' | Select-Object -First 1' + #13#10 +
    '$ffplay = Get-ChildItem -Path $extract -Recurse -Filter ''ffplay.exe'' | Select-Object -First 1' + #13#10 +
    'if ($null -eq $ffmpeg -or $null -eq $ffprobe -or $null -eq $ffplay) { throw ''ffmpeg.exe, ffprobe.exe oder ffplay.exe wurde im Archiv nicht gefunden.'' }' + #13#10 +
    'Copy-Item -Force $ffmpeg.FullName (Join-Path $tools ''ffmpeg.exe'')' + #13#10 +
    'Copy-Item -Force $ffprobe.FullName (Join-Path $tools ''ffprobe.exe'')' + #13#10 +
    'Copy-Item -Force $ffplay.FullName (Join-Path $tools ''ffplay.exe'')' + #13#10 +
    'Remove-Item -Recurse -Force $extract -ErrorAction SilentlyContinue' + #13#10 +
    'Remove-Item -Force $zip -ErrorAction SilentlyContinue' + #13#10;

  Result := RunPowerShell(Script, 'FFmpeg wird heruntergeladen (' + SourceName + ') ...');
end;

procedure DownloadFFmpeg();
begin
  if FileExists(ExpandConstant('{app}\tools\ffmpeg.exe')) and
     FileExists(ExpandConstant('{app}\tools\ffprobe.exe')) and
     FileExists(ExpandConstant('{app}\tools\ffplay.exe')) then
  begin
    Log('FFmpeg, FFprobe und FFplay sind bereits vorhanden.');
    exit;
  end;

  if DownloadFFmpegFromUrl('{#FFmpegUrl1}', 'BtbN') then
    exit;

  Log('BtbN-Download fehlgeschlagen. Versuche gyan.dev ...');

  if DownloadFFmpegFromUrl('{#FFmpegUrl2}', 'gyan.dev') then
    exit;

  MsgBox(
    'FFmpeg konnte nicht heruntergeladen oder entpackt werden.' + #13#10#13#10 +
    'Die Installation wird trotzdem fortgesetzt.' + #13#10 +
    'Du kannst FFmpeg später im Tool-Center nachinstallieren.',
    mbInformation,
    MB_OK
  );
end;

procedure DownloadDeno();
var
  ToolsDir: String;
  Script: String;
begin
  ToolsDir := ExpandConstant('{app}\tools');
  ForceDirectories(ToolsDir);

  if FileExists(ToolsDir + '\deno.exe') then
  begin
    Log('deno.exe ist bereits vorhanden.');
    exit;
  end;

  Script :=
    '$ErrorActionPreference = ''Stop''' + #13#10 +
    '$tools = ''' + EscapePS(ToolsDir) + '''' + #13#10 +
    '$zip = Join-Path $env:TEMP ''mediahub_deno.zip''' + #13#10 +
    '$extract = Join-Path $env:TEMP ''mediahub_deno_extract''' + #13#10 +
    'New-Item -ItemType Directory -Force -Path $tools | Out-Null' + #13#10 +
    'Remove-Item -Recurse -Force $extract -ErrorAction SilentlyContinue' + #13#10 +
    'Remove-Item -Force $zip -ErrorAction SilentlyContinue' + #13#10 +
    'Invoke-WebRequest -UseBasicParsing -Uri ''{#DenoUrl}'' -OutFile $zip' + #13#10 +
    'Expand-Archive -Force -Path $zip -DestinationPath $extract' + #13#10 +
    '$deno = Get-ChildItem -Path $extract -Recurse -Filter ''deno.exe'' | Select-Object -First 1' + #13#10 +
    'if ($null -eq $deno) { throw ''deno.exe wurde im Archiv nicht gefunden.'' }' + #13#10 +
    'Copy-Item -Force $deno.FullName (Join-Path $tools ''deno.exe'')' + #13#10 +
    'Remove-Item -Recurse -Force $extract -ErrorAction SilentlyContinue' + #13#10 +
    'Remove-Item -Force $zip -ErrorAction SilentlyContinue' + #13#10;

  if not RunPowerShell(Script, 'Deno wird heruntergeladen ...') then
  begin
    MsgBox(
      'Deno konnte nicht heruntergeladen werden.' + #13#10#13#10 +
      'Die Installation wird trotzdem fortgesetzt.' + #13#10 +
      'Du kannst Deno später im Tool-Center nachinstallieren.',
      mbInformation,
      MB_OK
    );
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if WizardIsTaskSelected('downloadtools\ytdlp') then
      DownloadYtDlp();

    if WizardIsTaskSelected('downloadtools\ffmpeg') then
      DownloadFFmpeg();

    if WizardIsTaskSelected('downloadtools\deno') then
      DownloadDeno();
  end;
end;

function AskDelete(Caption: String): Boolean;
begin
  Result :=
    MsgBox(
      Caption + ' wirklich löschen?' + #13#10#13#10 +
      'Ja = löschen' + #13#10 +
      'Nein = behalten',
      mbConfirmation,
      MB_YESNO
    ) = IDYES;
end;

function InitializeUninstall(): Boolean;
var
  DoAsk: Boolean;
begin
  DeleteDownloads := False;
  DeleteBackups := False;
  DeleteDatabase := False;
  DeleteConfig := False;
  DeleteLogs := False;
  DeletePlugins := False;
  DeleteTools := False;
  DeleteChannelAssets := False;

  DoAsk :=
    MsgBox(
      'MediaHub wird deinstalliert.' + #13#10#13#10 +
      'Persönliche Daten bleiben standardmäßig erhalten.' + #13#10 +
      'Möchtest du einzelne Datenordner zum Löschen auswählen?',
      mbConfirmation,
      MB_YESNO
    ) = IDYES;

  if DoAsk then
  begin
    if DirExists(ExpandConstant('{app}\downloads')) then
      DeleteDownloads := AskDelete('Downloads');

    if DirExists(ExpandConstant('{app}\backups')) then
      DeleteBackups := AskDelete('Backups');

    if DirExists(ExpandConstant('{app}\database')) or FileExists(ExpandConstant('{app}\config\mediahub.sqlite3')) then
      DeleteDatabase := AskDelete('Datenbank');

    if DirExists(ExpandConstant('{app}\config')) then
      DeleteConfig := AskDelete('Einstellungen');

    if DirExists(ExpandConstant('{app}\logs')) then
      DeleteLogs := AskDelete('Protokolle');

    if DirExists(ExpandConstant('{app}\plugins')) then
      DeletePlugins := AskDelete('Plugins');

    if DirExists(ExpandConstant('{app}\tools')) then
      DeleteTools := AskDelete('Tools');

    if DirExists(ExpandConstant('{app}\assets\channels')) then
      DeleteChannelAssets := AskDelete(
        'Kanalbilder, Banner und Playlistbilder' + #13#10 + #13#10 +
        'Diese Bilder wurden von MediaHub heruntergeladen und können später erneut geladen werden.'
      );
  end;

  Result := True;
end;

procedure DeleteDirIfChosen(ShouldDelete: Boolean; RelativePath: String);
var
  Target: String;
begin
  Target := ExpandConstant('{app}\' + RelativePath);

  if ShouldDelete then
  begin
    if DirExists(Target) then
    begin
      Log('Lösche: ' + Target);
      DelTree(Target, True, True, True);
    end;
  end
  else
  begin
    Log('Bleibt erhalten: ' + Target);
  end;
end;

procedure DeleteDatabaseFiles();
begin
  if not DeleteDatabase then
    exit;

  DeleteDirIfChosen(True, 'database');

  DeleteFile(ExpandConstant('{app}\config\mediahub.sqlite3'));
  DeleteFile(ExpandConstant('{app}\config\mediahub.sqlite3-wal'));
  DeleteFile(ExpandConstant('{app}\config\mediahub.sqlite3-shm'));
  DeleteFile(ExpandConstant('{app}\config\mediahub.sqlite3-journal'));
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DeleteDirIfChosen(DeleteDownloads, 'downloads');
    DeleteDirIfChosen(DeleteBackups, 'backups');
    DeleteDatabaseFiles();
    DeleteDirIfChosen(DeleteConfig, 'config');
    DeleteDirIfChosen(DeleteLogs, 'logs');
    DeleteDirIfChosen(DeletePlugins, 'plugins');
    DeleteDirIfChosen(DeleteTools, 'tools');
    DeleteDirIfChosen(DeleteChannelAssets, 'assets\channels');

    if DirExists(ExpandConstant('{app}\cache')) then
      DelTree(ExpandConstant('{app}\cache'), True, True, True);

    if DeleteDownloads then
    begin
      if DirExists(ExpandConstant('{app}\archive')) then
        DelTree(ExpandConstant('{app}\archive'), True, True, True);
    end;

    RemoveDir(ExpandConstant('{app}'));
  end;
end;
