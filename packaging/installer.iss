#define AppName "Boleto Extractor"
#define AppExe "BoletoExtractor.exe"
#define AppVersion "1.4.0"
#define AppPublisher "Wesllei"

[Setup]
AppId={{8E4B2C71-5A3D-4F0E-9B6A-1C2D3E4F5A60}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=..\dist\instalador
OutputBaseFilename=BoletoExtractor-Setup-{#AppVersion}
SetupIconFile=..\assets\icone.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktop"; Description: "Criar atalho na área de trabalho"; Flags: unchecked

[Files]
Source: "..\dist\BoletoExtractor\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktop

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent

[InstallDelete]
; Remove arquivos da versão anterior que podem sobrar
Type: filesandordirs; Name: "{app}\_internal"
