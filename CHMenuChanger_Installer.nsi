; =============================================================================
;  CHMenuChanger_Installer.nsi
;  NSIS installer script for CHMenuChanger by JURMR
;
;  Requirements:
;    - NSIS 3.x installed (https://nsis.sourceforge.io/Download)
;    - Run AFTER build.bat has produced dist\CHMenuChanger\
;    - Place this .nsi file in the same folder as build.bat
;
;  To compile:
;    Right-click CHMenuChanger_Installer.nsi -> "Compile NSIS Script"
;    OR from command line: makensis CHMenuChanger_Installer.nsi
;
;  Output: CHMenuChanger_Setup.exe  (in the same folder as this script)
; =============================================================================

!include "MUI2.nsh"
!include "LogicLib.nsh"

; ---------------------------------------------------------------------------
; Basic info
; ---------------------------------------------------------------------------
Name                "CHMenuChanger"
OutFile             "CHMenuChanger_Setup.exe"
InstallDir          "C:\CHMenuChanger"
InstallDirRegKey    HKCU "Software\CHMenuChanger" "InstallDir"
RequestExecutionLevel admin
SetCompressor       /SOLID lzma

; ---------------------------------------------------------------------------
; Version info (shows in installer window title and file properties)
; ---------------------------------------------------------------------------
VIProductVersion    "1.0.0.0"
VIAddVersionKey     "ProductName"     "CHMenuChanger"
VIAddVersionKey     "ProductVersion"  "1.0.0"
VIAddVersionKey     "CompanyName"     "JURMR"
VIAddVersionKey     "FileDescription" "CHMenuChanger Installer"
VIAddVersionKey     "FileVersion"     "1.0.0"
VIAddVersionKey     "LegalCopyright"  "JURMR"

; ---------------------------------------------------------------------------
; Macro: set "Run as administrator" flag on a .lnk shortcut file.
; Sets bit 5 of byte 21 in the LNK header -- no ShellLink plugin needed.
; Usage: !insertmacro SetRunAsAdmin "path\to\shortcut.lnk"
; ---------------------------------------------------------------------------
!macro SetRunAsAdmin LNK_PATH
    FileOpen $9 "${LNK_PATH}" r
    FileSeek $9 21
    FileReadByte $9 $8
    FileClose $9
    IntOp $8 $8 | 0x20
    FileOpen $9 "${LNK_PATH}" a
    FileSeek $9 21
    FileWriteByte $9 $8
    FileClose $9
!macroend

; ---------------------------------------------------------------------------
; UI settings
; ---------------------------------------------------------------------------
!define MUI_ABORTWARNING
!define MUI_ICON                    "E:\Downloads\JURMRWEED.ico"
!define MUI_UNICON                  "E:\Downloads\JURMRWEED.ico"
!define MUI_HEADERIMAGE
!define MUI_HEADERIMAGE_RIGHT
!define MUI_WELCOMEFINISHPAGE_BITMAP_NOSTRETCH

; Finish page -- offer to launch the app immediately
!define MUI_FINISHPAGE_RUN          "$INSTDIR\CHMenuChanger.exe"
!define MUI_FINISHPAGE_RUN_TEXT     "Launch CHMenuChanger"
!define MUI_FINISHPAGE_RUN_NOTCHECKED  ; unchecked by default -- user opts in

; ---------------------------------------------------------------------------
; Installer pages
; ---------------------------------------------------------------------------
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

; ---------------------------------------------------------------------------
; Uninstaller pages
; ---------------------------------------------------------------------------
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

; ---------------------------------------------------------------------------
; Language
; ---------------------------------------------------------------------------
!insertmacro MUI_LANGUAGE "English"

; ---------------------------------------------------------------------------
; Installer section
; ---------------------------------------------------------------------------
Section "CHMenuChanger" SecMain

    SectionIn RO  ; required, cannot be deselected

    SetOutPath "$INSTDIR"

    ; Copy everything from the build output
    File /r "dist\CHMenuChanger\*.*"

    ; Write install dir to registry (used by uninstaller and Start Menu shortcut)
    WriteRegStr HKCU "Software\CHMenuChanger" "InstallDir" "$INSTDIR"

    ; Write uninstall info to Add/Remove Programs
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "DisplayName" "CHMenuChanger"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "DisplayVersion" "1.0.0"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "Publisher" "JURMR"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "UninstallString" '"$INSTDIR\Uninstall.exe"'
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "DisplayIcon" "$INSTDIR\CHMenuChanger.exe"
    WriteRegDWORD HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "NoModify" 1
    WriteRegDWORD HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger" \
        "NoRepair" 1

    ; Create Start Menu shortcut (with "Run as administrator" flag)
    CreateDirectory "$SMPROGRAMS\CHMenuChanger"
    CreateShortcut \
        "$SMPROGRAMS\CHMenuChanger\CHMenuChanger.lnk" \
        "$INSTDIR\CHMenuChanger.exe" \
        "" \
        "$INSTDIR\CHMenuChanger.exe" \
        0 \
        SW_SHOWNORMAL \
        "" \
        "Change Clone Hero menu backgrounds"

    ; Set both shortcuts to always run as administrator
    !insertmacro SetRunAsAdmin "$SMPROGRAMS\CHMenuChanger\CHMenuChanger.lnk"

    ; Also create a Desktop shortcut
    CreateShortcut \
        "$DESKTOP\CHMenuChanger.lnk" \
        "$INSTDIR\CHMenuChanger.exe" \
        "" \
        "$INSTDIR\CHMenuChanger.exe" \
        0 \
        SW_SHOWNORMAL \
        "" \
        "Change Clone Hero menu backgrounds"

    !insertmacro SetRunAsAdmin "$DESKTOP\CHMenuChanger.lnk"

    ; Write the uninstaller
    WriteUninstaller "$INSTDIR\Uninstall.exe"

SectionEnd

; ---------------------------------------------------------------------------
; Uninstaller section
; ---------------------------------------------------------------------------
Section "Uninstall"

    ; Remove all installed files
    RMDir /r "$INSTDIR"

    ; Remove Start Menu folder
    RMDir /r "$SMPROGRAMS\CHMenuChanger"

    ; Remove Desktop shortcut
    Delete "$DESKTOP\CHMenuChanger.lnk"

    ; Remove registry entries
    DeleteRegKey HKCU "Software\CHMenuChanger"
    DeleteRegKey HKLM \
        "Software\Microsoft\Windows\CurrentVersion\Uninstall\CHMenuChanger"

SectionEnd
