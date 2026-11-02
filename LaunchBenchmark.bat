@echo off
rem Open the interactive 3D visual benchmark with type-in controls, not the old fixed-population G4 benchmark.
call "%~dp0RUN_G7_VISUAL_BENCHMARK.cmd" %*
exit /b %errorlevel%
