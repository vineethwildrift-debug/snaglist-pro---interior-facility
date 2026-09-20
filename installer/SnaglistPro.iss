; Inno Setup Script
; Compile with: "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" /O"output" "installer\SnaglistPro.iss"

[Setup]
AppName=Snaglist Pro
AppVersion=2.0.0
DefaultDirName={localappdata}\Snaglist Pro
DefaultGroupName=Snaglist Pro
AllowNoIcons=no
OutputBaseFilename=SnaglistPro-Setup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=lowest

[Files]
Source: "..\dist\SnaglistPro.exe"; DestDir: "{app}"

[Icons]
Name: "{group}\Snaglist Pro"; Filename: "{app}\SnaglistPro.exe"
Name: "{group}\Uninstall Snaglist Pro"; Filename: "{uninstallexe}"

[Run]
Filename: "{app}\SnaglistPro.exe"; Description: "Launch Snaglist Pro"; Flags: nowait postinstall skipifsilent
