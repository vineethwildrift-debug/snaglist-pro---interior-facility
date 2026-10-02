; Inno Setup Script
; Compile with: build_installer.bat (locates ISCC.exe automatically)

[Setup]
AppName=Snaglist Pro
AppVersion=2.0.3
AppPublisher=vineeth.raghu@indiqube.com
AppPublisherURL=mailto:vineeth.raghu@indiqube.com
AppSupportURL=mailto:vineeth.raghu@indiqube.com
AppCopyright=Copyright (c) 2026 vineeth.raghu@indiqube.com
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
