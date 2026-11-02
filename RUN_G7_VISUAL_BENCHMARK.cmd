@echo off
rem Interactive native Sunder G7 visual benchmark. Type population and other exact values in the window.
rem Unlike RUN_G7_RENDER_BENCHMARK.cmd this stays interactive until closed.
call "%~dp0LAUNCH_G7_CAPABILITIES_DEMO.cmd" %*
exit /b %errorlevel%
