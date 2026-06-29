; NSIS installer script for GentGranBD (Windows)
; Build with: makensis installer.nsi (after building pyinstaller-win.spec)

!include "FileFunc.nsh"

!define APPNAME "GentGranBD"
!ifndef VERSION
!define VERSION "1.0.0"
!endif
!define COMPANY "Gent Gran"
; Allow overriding DISTDIR from CLI: makensis -DDISTDIR=path installer.nsi
!ifndef DISTDIR
!define DISTDIR "dist\GentGranBD"
!endif
; Allow passing a single EXE path for one-file builds: makensis -DAPP_EXE=dist\GentGranBD.exe

OutFile "GentGranBD-Setup-${VERSION}.exe"
InstallDir "$PROGRAMFILES64\${COMPANY}\${APPNAME}"
RequestExecutionLevel admin

Page directory
Page instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  ; Replace the previous PyInstaller payload. User data lives in %APPDATA%\GentGranBD.
  Delete "$INSTDIR\GentGranBD.exe"
  RMDir /r "$INSTDIR\_internal"
  !ifdef APP_EXE
    File /oname=GentGranBD.exe "${APP_EXE}"
  !else
    File /r "${DISTDIR}\*.*"
  !endif
  CreateShortCut "$DESKTOP\${APPNAME}.lnk" "$INSTDIR\GentGranBD.exe"

  ${GetParameters} $R0
  ClearErrors
  ${GetOptions} "$R0" "/LAUNCH" $R1
  IfErrors done
  Exec "$INSTDIR\GentGranBD.exe"
done:
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\${APPNAME}.lnk"
  RMDir /r "$INSTDIR"
SectionEnd
