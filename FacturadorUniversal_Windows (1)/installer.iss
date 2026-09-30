#define MyAppName "Facturador Universal"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Facturador Universal"
#define MyAppExeName "FacturadorUniversal.exe"

[Setup]
AppId={{B7A7D98A-3F62-4B08-9A53-3F7F4E318200}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\FacturadorUniversal
DefaultGroupName={#MyAppName}
OutputDir=installer
OutputBaseFilename=FacturadorUniversal-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName={#MyAppName}

[Files]
Source: "dist\FacturadorUniversal\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Abrir {#MyAppName}"; Flags: nowait postinstall skipifsilent
