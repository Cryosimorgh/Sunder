@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Sunder P10 Native Windows Qualification

echo =========================================================
echo Sunder P10 - Actual Windows D3D12 qualification
echo This tests the GPU; it is not a benchmark-only simulation.
echo =========================================================
echo.
echo Do not close this window until both testing and evidence packaging finish.
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python 3 with NumPy is required on PATH.
    echo Install Python 3.12 and run: python -m pip install numpy
    echo No suite ran, so no native qualification can be claimed.
    goto :prereq_error
)

python run_world_sweep.py --full
set "SUITE_EXIT=%ERRORLEVEL%"
echo.
echo Native suite exit code: %SUITE_EXIT%
echo Packaging the original per-run logs, including failures...
echo.

python package_p10_evidence.py
set "PACKAGE_EXIT=%ERRORLEVEL%"

echo.
if not "%PACKAGE_EXIT%"=="0" (
    echo ERROR: Packaging failed. Keep the entire evidence/p10/world-sweep directory.
    echo Send the complete directory or retry: python package_p10_evidence.py
    goto :end
)
echo RESULT: See P10-RESULTS-TO-SEND folder in this repository.
echo Upload the newest Sunder-P10-*.zip into our conversation.
if not "%SUITE_EXIT%"=="0" (
    echo Qualification result: NO-GO or incomplete, based on original evidence.
) else (
    echo Scripted gates returned success. Reviewer must still inspect raw evidence.
)
goto :end

:prereq_error
set "SUITE_EXIT=2"
set "PACKAGE_EXIT=2"

:end
echo.
if not "%P10_NO_PAUSE%"=="1" pause
if not "%PACKAGE_EXIT%"=="0" exit /b %PACKAGE_EXIT%
exit /b %SUITE_EXIT%
