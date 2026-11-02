@echo off
setlocal
pushd "%~dp0"
set "BENCH_EXE=%~dp0GPUPhysicsBench.exe"
if not exist "%BENCH_EXE%" set "BENCH_EXE=%~dp0zig-out\bin\GPUPhysicsBench.exe"
"%BENCH_EXE%" %*
set "BENCH_EXIT=%errorlevel%"
popd
if not "%BENCH_EXIT%"=="0" echo GPU Physics Bench exited with error %BENCH_EXIT%.
exit /b %BENCH_EXIT%
