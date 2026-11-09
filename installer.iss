#define MyAppName "PT Clip Viewer"
#define MyAppVersion "3.9.11"
#define MyAppExeName "pt_clip_viewer.exe"

[Setup]
AppId={{D265FE18-89DF-48B5-8DA6-B5B94C9449EE}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher=JaminFX
DefaultDirName={localappdata}\Programs\PT Clip Viewer
DefaultGroupName={#MyAppName}
PrivilegesRequired=lowest
OutputDir=release
OutputBaseFilename=PT_Clip_Viewer_Setup_{#MyAppVersion}_Windows_x64
SetupIconFile=logo.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
SetupLogging=yes
VersionInfoVersion=3.9.11.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\pt_clip_viewer\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PT Clip Viewer"; Flags: nowait postinstall skipifsilent
