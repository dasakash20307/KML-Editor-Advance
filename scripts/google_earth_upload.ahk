; google_earth_upload.ahk
#SingleInstance force
SetTitleMatchMode 2 ; Match anywhere in title

; Retrieve command line parameters
historical_param := A_Args[1] ; First parameter passed from Python

; --- Configuration ---
; Adjust these window titles if Google Earth runs in a different browser or window
googleEarthWindowTitle := "Google Earth"
fileDialogOpenWindowTitle := "Open" ; Or "Import", depending on system/browser language
searchDurationMs := 5000 ; Max time to wait for a window
timeoutSeconds := searchDurationMs / 1000

; --- Main Logic ---

; 1. Activate Google Earth Window
WinWait, %googleEarthWindowTitle%,, %timeoutSeconds%
If ErrorLevel { ; WinWait timed out
    ExitApp ; Window not found
}
WinActivate, %googleEarthWindowTitle%
Sleep 300 ; Give it a moment to become active
Click 50 100 ; Click near top-left of the window to help focus

; 2. Open Import Dialog (Ctrl+I)
SendInput ^i
Sleep 500 ; Wait for dialog to appear

; 3. Paste File Path and Open
WinWait, %fileDialogOpenWindowTitle%,, %timeoutSeconds%
If ErrorLevel { ; WinWait timed out
    ExitApp ; File dialog not found
}
WinActivate, %fileDialogOpenWindowTitle% ; Ensure file dialog is active
Sleep 200
SendInput ^v ; Paste path from clipboard
Sleep 300
SendInput !o ; Alt+O to open/confirm. Could also be {Enter}
Sleep 1000 ; Give time for file to potentially load before next step

; 4. Enable Historical View (Conditional)
if (historical_param = "historical_on") {
    Sleep 3000 ; Wait a bit longer for KML to load visually before Ctrl+H

    ; Re-activate Google Earth Window as focus might have been lost
    If WinExist(googleEarthWindowTitle) { ; Using function call WinExist() is fine
        WinActivate, %googleEarthWindowTitle%
        Sleep 300
        SendInput ^h ; Ctrl+H for historical imagery
    }
    ; Removed MsgBox for "window lost focus"
}

ExitApp
