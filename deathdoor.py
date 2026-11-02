@echo off
setlocal enabledelayedexpansion

set "USB_DRIVE="
for /f "tokens=*" %%i in ('powershell -Noprofile -command "Get-CimInstance Win32_LogicalDisk | where-object DriveType -eq 2 | Select-object-ExpandProperty DeviceID" 2^>nul') do (
    if not defined USB_DRIVE set "USB_DRIVE=%%i"
)

if defined USB_DRIVE (
    set "OUTPUT_FILE=!USB_DRIVE!\wifi_passwords.txt"
) else (
    set
    "OUTPUT_FILE=%USERPROFILE%\Desktop\wifi_"
)