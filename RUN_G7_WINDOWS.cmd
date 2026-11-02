@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Sunder G7 - Dense D3D12 Native Benchmark
echo Sunder G7 native hardware benchmark - no CPU solver or simulated GPU.
echo This is HEADLESS. For interactive 3D spheres, run LAUNCH_G7_DEMO.cmd.
echo Default: full 1K, 10K, 100K, two independent runs each.
echo Run with --quick for a smoke-only (non-qualifying) handoff.
where python >nul 2>nul
if not errorlevel 1 goto :run

rem Python unavailable: still preserve a uniquely named failure handoff.
if not exist "G7-RESULTS-TO-SEND" mkdir "G7-RESULTS-TO-SEND"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$id=[DateTime]::UtcNow.ToString('yyyyMMddTHHmmssfffffffZ')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8); $folder=Join-Path 'G7-RESULTS-TO-SEND' ('Sunder-G7-NO-GO-'+$id); New-Item -ItemType Directory -Path $folder -Force | Out-Null; 'NO-GO: Python 3 / NumPy missing. Native suite NOT RUN.' | Set-Content (Join-Path $folder 'FAILURE.txt'); Compress-Archive -Path (Join-Path $folder '*') -DestinationPath ($folder+'.zip'); Remove-Item $folder -Recurse -Force"
echo NO-GO. Send the unique ZIP from G7-RESULTS-TO-SEND.
exit /b 2

:run
python run_g7_windows.py %*
set "RC=%ERRORLEVEL%"
echo.
echo G7 suite exit code: %RC%
echo Send the newest single Sunder-G7 ZIP from G7-RESULTS-TO-SEND.
echo Never treat compiler success, a mock adapter, or a quick run as GPU qualification.
if not "%G7_NO_PAUSE%"=="1" pause
exit /b %RC%
