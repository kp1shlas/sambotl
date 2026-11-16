; Inno Setup script for the SamboTL *client* installer.
;
; Produces a proper Windows installer (setup wizard) that installs the portable
; client to %LOCALAPPDATA%\Programs\SamboTLClient, creates a Start Menu entry and
; a Desktop shortcut, and registers an uninstaller.
;
; Build (from the project root, after `packaging\build.ps1`):
;   iscc packaging\client_installer.iss

#define MyAppName "SamboTL Client"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SamboTL"
#define MyAppExeName "SamboTLClient.exe"

[Setup]
; NOTE: the AppId is a stable unique identifier — do not change it.
AppId={{7C2E3F1A-9B4D-4E6A-8C1B-2D5F0A3E6B7C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\SamboTLClient
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
; The installer must be able to write the executable.
PrivilegesRequired=lowest
OutputDir=..\dist\installer
OutputBaseFilename=SamboTLClientSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; No admin rights needed for the client.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; The portable client built by PyInstaller.
Source: "..\dist\SamboTLClient.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
