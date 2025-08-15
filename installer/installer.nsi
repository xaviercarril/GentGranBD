; NSIS installer script for GentGranBD (Windows)
; Build with: makensis installer.nsi (after building pyinstaller-win.spec)

!define APPNAME "GentGranBD"
!define VERSION "1.0.0"
!define COMPANY "Gent Gran"
!define DISTDIR "dist\GentGranBD"

OutFile "GentGranBD-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\${COMPANY}\${APPNAME}"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${DISTDIR}\*.*"
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\GentGranBD.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
