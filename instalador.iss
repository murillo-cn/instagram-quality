; Instalador do Instagram Quality (Inno Setup 6). Gere com: ISCC.exe instalador.iss
#define AppName "Instagram Quality"
#define AppVer "1.0.0"

[Setup]
AppId={{6F3C8E5A-2B7D-4C1E-9A44-5D0B1E7F3A92}
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=Murillo
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\insta.exe
OutputDir=instalador
OutputBaseFilename=InstagramQuality-Setup-{#AppVer}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
CloseApplications=no

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Criar atalho na área de trabalho"; GroupDescription: "Atalhos:"; Flags: unchecked

[Files]
Source: "insta.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "installed.flag"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENCAS.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "ffmpeg-LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\insta.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\insta.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\insta.exe"; Description: "Abrir o {#AppName}"; Flags: nowait postinstall skipifsilent
