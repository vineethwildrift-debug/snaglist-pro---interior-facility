; Snaglist Pro Installer (NSIS 3.x)
; Installs SnaglistPro.exe, creates shortcuts, sets registry, configures AppData

!include "MUI2.nsh"
!include "x64.nsh"

; Modern UI Settings
!define MUI_ABORTWARNING
!define MUI_ICON "${NSISDIR}\Contrib\Graphics\Icons\modern-install.ico"
!define MUI_UNICON "${NSISDIR}\Contrib\Graphics\Icons\modern-uninstall.ico"

; Installer Settings
Name "Snaglist Pro"
OutFile "SnaglistPro-2.0.1-Installer.exe"
InstallDir "$PROGRAMFILES64\SnaglistPro"
InstallDirRegKey HKCU "Software\SnaglistPro" "InstallDir"

; Request admin privileges for registry/AppData setup
RequestExecutionLevel admin

; Pages
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_COMPONENTS
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

; Installer Sections
Section "Snaglist Pro Application" SecApp
  SetOutPath "$INSTDIR"
  
  ; Copy EXE and dependencies
  File "..\02_build\SnaglistPro.exe"
  File "..\01_source\license.pub"
  File "..\01_source\config.yaml"
  
  ; Create start menu shortcuts
  SetOutPath "$SMPROGRAMS\SnaglistPro"
  CreateShortcut "$SMPROGRAMS\SnaglistPro\Snaglist Pro.lnk" "$INSTDIR\SnaglistPro.exe"
  CreateShortcut "$SMPROGRAMS\SnaglistPro\Documentation.lnk" "$INSTDIR\README.md"
  CreateShortcut "$SMPROGRAMS\SnaglistPro\Uninstall.lnk" "$INSTDIR\uninstall.exe"
  
  ; Create desktop shortcut
  CreateShortcut "$DESKTOP\Snaglist Pro.lnk" "$INSTDIR\SnaglistPro.exe"
  
  ; Store install dir in registry
  WriteRegStr HKCU "Software\SnaglistPro" "InstallDir" "$INSTDIR"
  WriteRegStr HKCU "Software\SnaglistPro" "Version" "2.0.1"
  WriteRegStr HKCU "Software\SnaglistPro" "Publisher" "Snaglist Pro Team"
  
  ; Write uninstaller
  WriteUninstaller "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SnaglistPro" "DisplayName" "Snaglist Pro"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SnaglistPro" "UninstallString" "$INSTDIR\uninstall.exe"
  WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SnaglistPro" "DisplayVersion" "2.0.1"
  
  ; Create AppData directories
  CreateDirectory "$LOCALAPPDATA\SnaglistPro"
  CreateDirectory "$LOCALAPPDATA\SnaglistPro\exports"
  CreateDirectory "$LOCALAPPDATA\SnaglistPro\license"
  CreateDirectory "$LOCALAPPDATA\SnaglistPro\database"
  
  ; Copy default config to AppData (user can edit)
  IfFileExists "$LOCALAPPDATA\SnaglistPro\config.yaml" +2
    CopyFiles "$INSTDIR\config.yaml" "$LOCALAPPDATA\SnaglistPro\config.yaml"
  
SectionEnd

Section "Documentation" SecDocs
  SetOutPath "$INSTDIR"
  File "..\04_docs\README.md"
  File "..\04_docs\QUICKSTART.md"
  File "..\04_docs\LICENSE_GUIDE.md"
  File "..\04_docs\ENV_VARS.md"
  File "..\04_docs\SECURITY_REVIEW.md"
  File "..\04_docs\CHANGELOG.md"
SectionEnd

Section "Sample Data" SecSamples
  SetOutPath "$LOCALAPPDATA\SnaglistPro\samples"
  File /r "..\03_sample_data\*"
SectionEnd

; Descriptions
LangString DESC_SecApp ${LANG_ENGLISH} "Core Snaglist Pro application and shortcuts."
LangString DESC_SecDocs ${LANG_ENGLISH} "Documentation, guides, and quick-start."
LangString DESC_SecSamples ${LANG_ENGLISH} "Sample data for testing and reference."

!insertmacro MUI_FUNCTION_DESCRIPTION_BEGIN
  !insertmacro MUI_DESCRIPTION_TEXT ${SecApp} $(DESC_SecApp)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecDocs} $(DESC_SecDocs)
  !insertmacro MUI_DESCRIPTION_TEXT ${SecSamples} $(DESC_SecSamples)
!insertmacro MUI_FUNCTION_DESCRIPTION_END

; Uninstaller
Section "Uninstall"
  RMDir /r "$SMPROGRAMS\SnaglistPro"
  Delete "$DESKTOP\Snaglist Pro.lnk"
  RMDir /r "$INSTDIR"
  DeleteRegKey HKCU "Software\SnaglistPro"
  DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\SnaglistPro"
  
  ; Leave AppData (user data preservation)
  MessageBox MB_YESNO "Remove all local data and licenses?$\nClick Yes to delete $LOCALAPPDATA\SnaglistPro" IDYES DeleteAppData IDNO SkipAppData
  DeleteAppData:
    RMDir /r "$LOCALAPPDATA\SnaglistPro"
  SkipAppData:
SectionEnd
