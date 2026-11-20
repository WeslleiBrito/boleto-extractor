#define AppName "Extrator de Boletos"
#define AppVersion "1.0.0"
#define AppExe "ExtratorBoletos.exe"
#define AppPublisher "Sua Empresa"
#define IconFile AddBackslash(SourcePath) + "icone.ico"

[Setup]
; Gere um GUID novo uma única vez (Tools > Generate GUID) e NUNCA mude depois
AppId={{8F3C2A71-5B4D-4E9A-9C1F-2D7E6A0B4C13}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\ExtratorBoletos
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\dist\instalador
OutputBaseFilename=ExtratorBoletos-Setup-{#AppVersion}
#if FileExists(IconFile)
SetupIconFile={#IconFile}
#else
  #pragma warning "icone.ico não encontrado em packaging\ — usando ícone padrão do Inno Setup."
#endif
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na Área de Trabalho"; GroupDescription: "Atalhos:"

[Files]
Source: "..\dist\ExtratorBoletos\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{group}\Desinstalar {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
