; google_earth_upload.ahk
; Removed #SingleInstance force for v2
SetTitleMatchMode(2) ; Match anywhere in title (v2)

; --- Configuration ---
; Adjust these window titles if Google Earth runs in a different browser or window
googleEarthWindowTitle := "Google Earth"
fileDialogOpenWindowTitle := "Open" ; Or "Import", depending on system/browser language
searchDurationMs := 5000 ; Max time to wait for a window
timeoutSeconds := searchDurationMs / 1000 ; Pre-calculate for v2 function calls

; --- Main Logic ---
historical_param := A_Args[1] ; First parameter passed from Python (v2 compatible)

; 1. Activate Google Earth Window
FoundWin := WinWait(googleEarthWindowTitle, "", timeoutSeconds) ; v2
If !FoundWin { ; v2: WinWait returns 0 on timeout (falsey)
    ExitApp() ; v2
}
WinActivate(googleEarthWindowTitle) ; v2
Sleep(300) ; v2: Give it a moment to become active
Click(50, 100) ; v2: Click near top-left of the window to help focus
Sleep(300) ; v2: Added small delay after click

; 2. Open Import Dialog (Ctrl+I)
SendInput("^i") ; v2: Parameters are typically strings
Sleep(500) ; v2: Wait for dialog to appear

; 3. Paste File Path and Open
FoundDialog := WinWait(fileDialogOpenWindowTitle, "", timeoutSeconds) ; v2
If !FoundDialog { ; v2
    ExitApp() ; v2
}
WinActivate(fileDialogOpenWindowTitle) ; v2: Ensure file dialog is active
Sleep(200) ; v2
SendInput("^v") ; v2: Paste path from clipboard
Sleep(300) ; v2
SendInput("!o") ; v2: Alt+O to open/confirm. Could also be "{Enter}"
Sleep(1000) ; v2: Give time for file to potentially load before next step

; 4. Enable Historical View (Conditional)
if (historical_param == "historical_on") { ; v2: == for case-sensitive string comparison
    Sleep(3000) ; v2: Wait a bit longer for KML to load visually before Ctrl+H

    ; Re-activate Google Earth Window as focus might have been lost
    if WinExist(googleEarthWindowTitle) { ; v2: This function call is fine
        WinActivate(googleEarthWindowTitle) ; v2
        Sleep(300) ; v2
        SendInput("^h") ; v2: Ctrl+H for historical imagery
    }
}

ExitApp() ; v2
