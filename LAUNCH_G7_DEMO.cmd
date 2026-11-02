@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Sunder G7 - Interactive Native 3D Demo
echo ===================================================
echo Sunder G7 visual demo - native D3D12 physics
echo 3D orbitable cube volume and colliding asteroid belts
echo This demo does NOT measure production-path performance.
echo ===================================================
where python >nul 2>nul
if errorlevel 1 (
  echo ERROR: Python 3.12 with NumPy and tkinter required.
  exit /b 2
)
if not exist "evidence\p10\build\physics3.dll" (
  echo Physics3 native DLL not found. Building native D3D12 physics...
  python build_physics3.py
  if errorlevel 1 (
    echo Native build failed. See build output.
    exit /b 1
  )
)
python g7_visual_demo.py %*
set "RESULT=%ERRORLEVEL%"
if not "%RESULT%"=="0" (
  echo G7 visual demo failed with exit code %RESULT%.
  if not "%G7_NO_PAUSE%"=="1" pause
)
exit /b %RESULT%
