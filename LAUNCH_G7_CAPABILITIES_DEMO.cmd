@echo off
setlocal
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
 echo Install Python 3.12 and add it to PATH. See docs/G7_DENSE_WORKLOADS.md.
 if not "%G7_NO_PAUSE%"=="1" pause
 exit /b 1
)
python build_g7_demo.py
if errorlevel 1 (
 echo Native build failed. See evidence/g7/native-showcase/build-*.log.
 if not "%G7_NO_PAUSE%"=="1" pause
 exit /b 1
)
zig-out\bin\SunderG7.exe %*
set "G7_RESULT=%errorlevel%"
if not "%G7_RESULT%"=="0" if not "%G7_NO_PAUSE%"=="1" pause
exit /b %G7_RESULT%
